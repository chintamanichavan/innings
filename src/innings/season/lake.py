"""The data lake: every simulated ball as a row in Parquet files, and how they get there.

The lake is a small star. `balls` is the one huge table. Its columns are short numbers that
point into four tiny tables: `matches`, `people`, `teams` and `outcomes`. Each writer reads
its own partitions of the Kafka topic, unpacks whole matches into rows, and appends them.
"""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from ..config import DATA
from ..nn.features import OUTCOME_IS_LEGAL, OUTCOME_RUNS, OUTCOMES, PAD, WICKET
from ..stream import wire
from .fixtures import Season
from .record import THE_END, unpack

LAKE = DATA / "lake"
MATCHES_AT_ONCE = 8000          # about two million balls a batch
ROWS_PER_FILE = 60_000_000

BALLS = pa.schema([
    ("season", pa.int32()), ("match", pa.int8()), ("innings", pa.int8()),
    ("ball", pa.uint8()),         # the delivery's number within its innings, from 0
    ("over", pa.int8()), ("bat_team", pa.int8()),
    ("batter", pa.int16()), ("bowler", pa.int16()),   # numbers of `people`
    ("outcome", pa.int8()),       # a number of `outcomes`
])
MATCHES = pa.schema([("season", pa.int32()), ("match", pa.int8()), ("home", pa.int8()), ("away", pa.int8()),
                     ("first", pa.int8()), ("winner", pa.int8())])


def balls_of(records: np.ndarray, season: Season) -> dict[str, np.ndarray]:
    """Unpack match records into one row for every ball bowled. No loop: all matches at once."""
    outcomes, strikers = records["outcomes"], records["strikers"]            # [match, innings, delivery]
    bowled = outcomes != PAD
    legal = (OUTCOME_IS_LEGAL == 1)[np.minimum(outcomes, PAD - 1)] & bowled
    over = np.minimum((np.cumsum(legal, axis=2) - legal) // 6, 19)

    # Who batted in each innings: the side that batted first, then the other.
    first = records["first"].astype(np.int64)
    batting = np.stack([first, 1 - first], axis=1)                           # [match, innings] a side
    team = np.stack([records["home"], records["away"]], axis=1).astype(np.int64)
    row = np.arange(len(records))[:, None]
    league = records["match"] < len(season.sides)
    at = np.minimum(records["match"], len(season.sides) - 1)[:, None]

    def squad(league_table: np.ndarray, usual: np.ndarray, side: np.ndarray) -> np.ndarray:
        """Each innings' eleven or its bowling plan: the match's own in the league, the usual one after."""
        return np.where(league[:, None, None], league_table[at, side], usual[team[row, side]])

    batter = np.take_along_axis(squad(season.order, season.usual_order, batting), strikers, axis=2)
    bowler = np.take_along_axis(squad(season.plan, season.usual_plan, 1 - batting), over, axis=2)

    def spread(values: np.ndarray) -> np.ndarray:
        """A value per match, per innings, or per match and innings, given to each of its balls."""
        per_innings = values[:, None] if values.shape == (len(records),) else values
        return np.broadcast_to(np.expand_dims(per_innings, -1), outcomes.shape)[bowled]

    return {
        "season": spread(records["season"]), "match": spread(records["match"]),
        "innings": spread(np.array([1, 2])),
        "ball": np.broadcast_to(np.arange(outcomes.shape[2]), outcomes.shape)[bowled],
        "over": over[bowled], "bat_team": spread(team[row, batting]),
        "batter": batter[bowled], "bowler": bowler[bowled], "outcome": outcomes[bowled],
    }


def _table(columns: dict[str, np.ndarray], schema: pa.Schema) -> pa.Table:
    return pa.table([pa.array(columns[field.name], type=field.type) for field in schema], schema=schema)


class _Files:
    """Parquet files of one table, a new one started whenever the current one is full."""

    def __init__(self, folder: Path, name: str, schema: pa.Schema):
        self.folder, self.name, self.schema = folder, name, schema
        self.folder.mkdir(parents=True, exist_ok=True)
        self.writer, self.rows_in_file, self.files, self.rows = None, 0, 0, 0

    def add(self, table: pa.Table) -> None:
        if self.writer is None or self.rows_in_file >= ROWS_PER_FILE:
            self.close()
            path = self.folder / f"{self.name}-{self.files:03d}.parquet"
            self.writer, self.rows_in_file = pq.ParquetWriter(path, self.schema, compression="zstd"), 0
            self.files += 1
        self.writer.write_table(table)
        self.rows_in_file += len(table)
        self.rows += len(table)

    def close(self) -> None:
        if self.writer is not None:
            self.writer.close()


def write(topic: str, partitions: list[int], season: Season) -> dict:
    """Read these partitions to their end marker, writing every ball and every match to the lake."""
    reader = wire.reader_of(topic, partitions)
    name = f"part-{partitions[0]}"
    balls, matches = _Files(LAKE / "balls", name, BALLS), _Files(LAKE / "matches", name, MATCHES)
    still_open, started = len(partitions), time.time()
    while still_open:
        payloads = [message.value() for message in wire.ready(reader, MATCHES_AT_ONCE, wait=1.0)]
        if not payloads:
            continue
        records = unpack(payloads)
        still_open -= int((records["season"] == THE_END).sum())
        records = records[records["season"] != THE_END]
        if len(records):
            balls.add(_table(balls_of(records, season), BALLS))
            matches.add(_table({name: records[name] for name in MATCHES.names}, MATCHES))
    balls.close()
    matches.close()
    reader.close()
    return {"balls": balls.rows, "matches": matches.rows, "seconds": round(time.time() - started, 2)}


def start_afresh(season: Season) -> None:
    """Empty the lake and write its small tables: the teams, the people and the outcomes."""
    shutil.rmtree(LAKE, ignore_errors=True)
    LAKE.mkdir(parents=True)
    pq.write_table(pa.table({"team": np.arange(len(season.teams), dtype=np.int8), "name": season.teams}),
                   LAKE / "teams.parquet")
    pq.write_table(pa.table({"person": np.arange(len(season.people), dtype=np.int16),
                             "player_id": [player_id for player_id, _ in season.people],
                             "name": [name for _, name in season.people]}), LAKE / "people.parquet")
    pq.write_table(pa.table({
        "outcome": np.arange(len(OUTCOMES), dtype=np.int8), "name": OUTCOMES,
        "runs": OUTCOME_RUNS.astype(np.int8),
        "bat_runs": np.where(np.arange(len(OUTCOMES)) < WICKET, OUTCOME_RUNS, 0).astype(np.int8),
        "legal": OUTCOME_IS_LEGAL == 1, "wicket": np.arange(len(OUTCOMES)) == WICKET,
    }), LAKE / "outcomes.parquet")


def size() -> dict:
    """What the lake holds on disk, read from the files' own footers."""
    files = sorted((LAKE / "balls").glob("*.parquet"))
    return {"files": len(files), "rows": sum(pq.ParquetFile(path).metadata.num_rows for path in files),
            "bytes": sum(path.stat().st_size for path in LAKE.rglob("*.parquet"))}


def main(topic: str, partitions: list[int], season: Season) -> None:
    print(json.dumps(write(topic, partitions, season)), flush=True)
