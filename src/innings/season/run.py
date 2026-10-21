"""The whole job, start to finish: play the seasons, stream them, fill the lake, ask the questions.

    simulator (graphics card)  ->  Kafka  ->  lake writers  ->  Parquet files  ->  DuckDB
                                         \\->  tally         ->  the live page
"""
from __future__ import annotations

import json
import struct
import subprocess
import sys
import time

from ..db import connect
from ..nn import gpu
from ..stream import wire
from . import findings, lake, simulate, tally
from .engine import Engine
from .fixtures import Season, load

REPORT = tally.FOLDER / "report.json"
LEAGUE = "IPL"


def season_of(year: int) -> tuple[Season, dict]:
    """The season's fixtures and the network's vocabulary. Every program in the job starts here."""
    vocabulary = json.loads((gpu.FOLDER / "vocabulary.json").read_text())
    con = connect(read_only=True)
    season = load(con, year, vocabulary)
    con.close()
    return season, vocabulary


def _helper(*arguments: str) -> subprocess.Popen:
    """Start another part of the job as its own program."""
    return subprocess.Popen([sys.executable, "-m", "innings.cli", "season", *arguments],
                            stdout=subprocess.PIPE, text=True)


def run(year: int, seasons: int, seed: int = 0) -> dict:
    season, vocabulary = season_of(year)
    topic = f"season-{int(time.time())}"
    wire.ensure_topics(topic)
    lake.start_afresh(season)
    started = time.time()

    writers = [_helper("lake", topic, str(partition), str(year)) for partition in range(wire.PARTITIONS)]
    counter = _helper("tally", topic, str(year), str(seasons))

    model, _ = gpu.load()
    engine = Engine(model, year, vocabulary["leagues"][LEAGUE], seed)
    writer = wire.producer()
    made = simulate.run(engine, season, seasons, seed=seed,
                        send=lambda number, payload: wire.send_bytes(
                            writer, topic, struct.pack("<I", number), payload))
    for partition in range(wire.PARTITIONS):
        writer.produce(topic, simulate.end_marker(), partition=partition)
    writer.flush()

    written = [json.loads(helper.communicate()[0].strip().splitlines()[-1]) for helper in writers]
    counter.wait()
    streamed = time.time() - started
    wire.delete_topics(topic)

    counted = json.loads(tally.LIVE.read_text())
    in_lake = lake.size()
    report = {
        "year": year, "made": made, "seconds": round(streamed, 1),
        "balls_per_second": round(made["balls"] / streamed),
        "lake": in_lake | {"writers": len(writers),
                           "rows_per_second": round(in_lake["rows"] / max(w["seconds"] for w in written))},
        # Nothing lost and nothing doubled: three programs counted the balls and must agree.
        "counts": {"simulator": made["balls"], "tally": counted["balls"], "lake": in_lake["rows"]},
        "findings": findings.run(), "at": time.strftime("%Y-%m-%d"),
    }
    REPORT.write_text(json.dumps(report, indent=1))
    return report
