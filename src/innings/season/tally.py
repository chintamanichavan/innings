"""Keeps the running count: who has won the title so far, as the seasons come off the stream.

The tally reads every match message. From each it takes the few header bytes and counts the
balls. It rewrites one small file about once a second, which is what the page watches.
"""
from __future__ import annotations

import json
import os
import time

import numpy as np

from ..config import SEASON
from ..nn.features import PAD
from ..stream import wire
from .fixtures import PLAYOFFS, Season
from .record import THE_END, unpack

FOLDER = SEASON
LIVE = FOLDER / "tally.json"
MATCHES_AT_ONCE = 20_000
WRITE_EVERY = 1.0          # seconds between rewrites of the live file
FIRST_LOOK = 10            # the odds are first noted after this many seasons, then about 8% more each time
LOOK_GROWTH = 1.08


class Tally:
    def __init__(self, season: Season, target: int):
        self.season, self.target = season, target
        teams = len(season.teams)
        self.titles = np.zeros(teams, dtype=np.int64)
        self.finals = np.zeros(teams, dtype=np.int64)       # seasons in which the team reached the final
        self.playoffs = np.zeros(teams, dtype=np.int64)
        self.league_wins = np.zeros(teams, dtype=np.int64)
        self.matches = self.balls = 0
        self.history: list[dict] = []                       # the title odds as they settled
        self.next_look = FIRST_LOOK
        self.started = time.time()

    @property
    def seasons(self) -> int:
        return int(self.titles.sum())

    def take(self, records: np.ndarray) -> None:
        """Count a batch of matches."""
        league = len(self.season.sides)
        winner = np.where(records["winner"] == 0, records["home"], records["away"])
        self.matches += len(records)
        self.balls += int((records["outcomes"] != PAD).sum())
        teams = len(self.titles)
        self.league_wins += np.bincount(winner[records["match"] < league], minlength=teams)

        # The four who play Qualifier 1 and the Eliminator are the four who made the playoffs.
        opening = (records["match"] == league) | (records["match"] == league + 1)
        for side in ("home", "away"):
            self.playoffs += np.bincount(records[side][opening], minlength=teams)
        final = records["match"] == league + len(PLAYOFFS) - 1
        for side in ("home", "away"):
            self.finals += np.bincount(records[side][final], minlength=teams)
        # A batch can hold many finals. Note the odds each time a looking point is passed.
        for champion in winner[final].tolist():
            self.titles[champion] += 1
            if self.seasons >= self.next_look:
                self.history.append({"seasons": self.seasons, "title": self._share(self.titles)})
                self.next_look = max(self.next_look + 1, int(self.next_look * LOOK_GROWTH))

    def _share(self, counts: np.ndarray) -> list[float]:
        return (counts / max(self.seasons, 1)).round(5).tolist()

    def report(self, running: bool) -> dict:
        seconds = time.time() - self.started
        return {
            "year": self.season.year, "teams": self.season.teams, "running": running,
            "target": self.target, "seasons": self.seasons, "matches": self.matches, "balls": self.balls,
            "seconds": round(seconds, 1), "balls_per_second": round(self.balls / max(seconds, 1e-9)),
            "title": self._share(self.titles), "final": self._share(self.finals),
            "playoffs": self._share(self.playoffs),
            "league_wins": (self.league_wins / max(self.seasons, 1)).round(3).tolist(),
            "history": self.history, "real": self.season.real,
        }

    def save(self, running: bool) -> None:
        FOLDER.mkdir(parents=True, exist_ok=True)
        unfinished = LIVE.with_suffix(".writing")
        unfinished.write_text(json.dumps(self.report(running)))
        os.replace(unfinished, LIVE)   # the page never reads half a file


def run(topic: str, season: Season, target: int) -> dict:
    """Read every partition to its end marker, keeping the live file up to date."""
    reader = wire.reader_of(topic, list(range(wire.PARTITIONS)))
    tally = Tally(season, target)
    still_open, last_write = wire.PARTITIONS, 0.0
    while still_open:
        payloads = [message.value() for message in wire.ready(reader, MATCHES_AT_ONCE, wait=0.5)]
        if payloads:
            records = unpack(payloads)
            still_open -= int((records["season"] == THE_END).sum())
            tally.take(records[records["season"] != THE_END])
        if time.time() - last_write > WRITE_EVERY:
            tally.save(running=True)
            last_write = time.time()
    tally.history.append({"seasons": tally.seasons, "title": tally._share(tally.titles)})
    tally.save(running=False)
    reader.close()
    return tally.report(running=False)
