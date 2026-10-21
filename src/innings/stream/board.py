"""The scoreboard inside the API server: the end of the stream.

One thread reads every scored ball from Kafka and keeps the matches now in play in memory.
The web routes read from here; they never touch Kafka themselves.
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from collections import deque

from . import bench, wire

LINGER = 30.0       # a finished match stays on the board this many seconds
ABANDONED = 120.0   # a match with no news for this long is taken down: its bowler was stopped
RECENT = 400        # records kept for late joiners and for the speed and delay figures
RETRY = 5.0         # seconds between tries while Kafka is not there
MATCH_FACTS = ("match_id", "fmt", "competition", "team1", "team2", "venue", "date")


class Board:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.matches: dict[str, dict] = {}      # match -> its facts and every point of its chart
        self.recent: deque[dict] = deque(maxlen=RECENT)
        self.count = 0                          # records taken so far; each record's number
        self.connected = False

    def take(self, record: dict, now: float) -> None:
        """Add one scored record to the board."""
        match_id = record["match_id"]
        if record["kind"] == "start":
            self.matches[match_id] = {name: record[name] for name in MATCH_FACTS} | {"points": []}
        elif match_id not in self.matches:
            return   # a match that was already under way when this server started
        elif self.matches[match_id]["points"] and record["n"] <= self.matches[match_id]["points"][-1]["n"]:
            return   # a scorer that restarted may answer its last few balls twice
        self.count += 1
        record["id"], record["seen_at"] = self.count, now
        self.recent.append(record)
        if record["kind"] != "start":
            self.matches[match_id]["points"].append(record)

    def tidy(self, now: float) -> None:
        """Take down matches that finished a while ago."""
        for match_id, match in list(self.matches.items()):
            if not match["points"]:
                continue
            last = match["points"][-1]
            quiet_for = now - last["scored_at"]
            if quiet_for > (LINGER if last["kind"] == "end" else ABANDONED):
                del self.matches[match_id]

    def figures(self, now: float) -> dict:
        """How the pipeline is doing right now: its speed and how long a ball takes to cross it."""
        balls = [record for record in self.recent
                 if record["kind"] == "ball" and now - record["seen_at"] < 10]
        delays = sorted(record["seen_at"] - record["sent_at"] for record in balls if record["sent_at"])
        return {"connected": self.connected, "taken": self.count, "matches": len(self.matches),
                "per_second": len(balls) / 10,
                "delay_ms": 1000 * delays[len(delays) // 2] if delays else None,
                "slowest_ms": 1000 * delays[-1] if delays else None}

    def snapshot(self) -> dict:
        """Everything a page needs when it first opens."""
        now = time.time()
        with self.lock:
            return {"on": enabled(), "matches": list(self.matches.values()), "cursor": self.count,
                    "figures": self.figures(now), "bench": _bench()}

    def since(self, cursor: int) -> dict:
        """What has happened since record number `cursor`."""
        now = time.time()
        with self.lock:
            if cursor < self.count - len(self.recent):
                return {"reload": True}   # too far behind to catch up from memory
            return {"records": [record for record in self.recent if record["id"] > cursor],
                    "cursor": self.count, "figures": self.figures(now)}

    def follow(self) -> None:
        """Read the scored topic for ever, from its start, so a restart rebuilds the board."""
        while True:
            try:
                wire.ensure_topics(wire.SCORED)
                reader = wire.consumer(f"board-{uuid.uuid4().hex[:8]}", from_start=True)
                reader.subscribe([wire.SCORED])
                self.connected = True
                while True:
                    records = wire.read(reader, 500, wait=0.2)
                    now = time.time()
                    with self.lock:
                        for record in records:
                            self.take(record, now)
                        self.tidy(now)
            except Exception as problem:   # Kafka is down or still starting: keep the site up, try again
                self.connected = False
                print(f"stream board: {problem}", flush=True)
                time.sleep(RETRY)


def _bench() -> list[dict]:
    return json.loads(bench.RESULTS.read_text()) if bench.RESULTS.exists() else []


def enabled() -> bool:
    """The stream is on only where a broker has been named."""
    return bool(os.environ.get("INNINGS_KAFKA"))


board = Board()


def start() -> None:
    if enabled():
        threading.Thread(target=board.follow, daemon=True, name="stream-board").start()
