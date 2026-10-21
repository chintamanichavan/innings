"""How fast is the stream, and is it still right at full speed?

Pushes whole matches through Kafka as fast as they will go, with a chosen number of scorers
sharing the work, then checks every answer against the numbers the build worked out.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from collections.abc import Iterator

from confluent_kafka import ConsumerGroupState, KafkaException
from confluent_kafka.admin import AdminClient

from ..config import DATA
from ..db import connect
from . import check, feed, wire

RESULTS = DATA / "stream" / "bench.json"
QUIET = 30.0   # seconds without a record before the run is called stuck


def _wait_for_group(group: str, members: int) -> None:
    """Hold on until every scorer has joined and Kafka has finished sharing out the partitions."""
    admin = AdminClient({"bootstrap.servers": wire.brokers()})
    for _ in range(240):
        time.sleep(0.5)
        try:
            described = admin.describe_consumer_groups([group])[group].result()
        except KafkaException:
            continue   # the group does not exist until its first scorer arrives
        if len(described.members) == members and described.state == ConsumerGroupState.STABLE:
            return
    raise TimeoutError(f"the {members} scorers did not all join")


def _scored(sink: str, group: str, expected: int, timing: dict) -> Iterator[dict]:
    """Every record the scorers wrote, noting when the last one was scored."""
    reader = wire.consumer(f"{group}-check", from_start=True)
    reader.subscribe([sink])
    seen, last_heard = 0, time.time()
    while seen < expected:
        records = wire.read(reader, 5000, wait=1.0)
        if records:
            last_heard = time.time()
        elif time.time() - last_heard > QUIET:
            raise TimeoutError(f"{seen:,} of {expected:,} records arrived, then nothing")
        for record in records:
            seen += 1
            timing["finished"] = max(timing.get("finished", 0), record["scored_at"])
            yield record
    reader.close()


def run(scorers: int, matches: int) -> dict:
    name = f"bench-{int(time.time())}"
    source, sink = f"{name}-balls", f"{name}-scored"
    wire.ensure_topics(source, sink)
    command = [sys.executable, "-m", "innings.cli", "stream", "score",
               "--group", name, "--source", source, "--sink", sink]
    one_core = os.environ | {"OMP_NUM_THREADS": "1"}   # so that adding scorers is a fair test
    workers = [subprocess.Popen(command, env=one_core, stdout=subprocess.DEVNULL) for _ in range(scorers)]
    try:
        _wait_for_group(name, scorers)
        con = connect(read_only=True)
        match_ids = feed.playable_ids(con, matches)
        writer, sent, balls = wire.producer(), 0, 0
        started = time.time()
        for message in feed.messages(con, match_ids):
            wire.send(writer, source, message)
            sent += 1
            balls += message["kind"] == "ball"
            if sent % 10_000 == 0:
                writer.poll(0)
        writer.flush()
        sending = time.time() - started

        timing: dict = {}
        streamed = check.after_each_ball(_scored(sink, name, sent, timing))
        built = con.execute("select match_id, seq, wp1_post from ck_ev where match_id in (select unnest(?))",
                            [match_ids]).fetchall()
        worst = max(abs(streamed[match_id, seq] - chance) for match_id, seq, chance in built)
        seconds = timing["finished"] - started
    finally:
        for worker in workers:
            worker.terminate()
        wire.delete_topics(source, sink)
    return {"scorers": scorers, "matches": len(match_ids), "balls": balls, "seconds": round(seconds, 2),
            "per_second": round(balls / seconds), "sent_per_second": round(sent / sending),
            "checked": len(built), "worst_difference": worst, "at": time.strftime("%Y-%m-%d")}


def record(result: dict) -> None:
    """Keep the latest run for each number of scorers, for the page to show."""
    runs = json.loads(RESULTS.read_text()) if RESULTS.exists() else []
    runs = [run for run in runs if run["scorers"] != result["scorers"]] + [result]
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(sorted(runs, key=lambda run: run["scorers"]), indent=1))
