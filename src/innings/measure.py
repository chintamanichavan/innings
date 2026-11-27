"""Measure the build and the site, so each change to the data platform can be compared.

`innings measure` rebuilds the database from the files already downloaded (no network),
timing each step, then records the sizes on disk and how fast the API answers the
pages people open most. The result is written to data/measure/<date>.json; the file
from before a change is the baseline that change is judged against.

The rebuild is a real one: it replaces the database, as `innings all` would.
"""
from __future__ import annotations

import json
import statistics
import time
from datetime import date
from pathlib import Path

from .config import DATA, DB_PATH, RAW

OUT = DATA / "measure"
WARM_CALLS = 20          # calls per endpoint after the first (cold) one
SAMPLE_PLAYER = "ba607b88"   # Virat Kohli: a long career in every format

ENDPOINTS = [
    ("front page", "/api/home", {"sport": "ck"}),
    ("leaderboard", "/api/leaders", {"sport": "ck", "role": "bat", "league": "IPL", "year": 2025}),
    ("player", f"/api/player/ck/{SAMPLE_PLAYER}", {}),
    ("player extra", f"/api/player-extra/ck/{SAMPLE_PLAYER}", {}),
    ("career", f"/api/career/{SAMPLE_PLAYER}", {}),
    ("match list", "/api/matches", {"sport": "ck", "league": "IPL"}),
    ("match", "/api/match/ck/{match}", {}),
    ("scorecard", "/api/scorecard/{match}", {}),
    ("commentary", "/api/commentary/{match}", {}),
    ("records", "/api/records", {"sport": "ck"}),
    ("team ratings", "/api/ratings", {"sport": "ck", "pool": "IPL"}),
    ("matchups", "/api/slice", {"role": "bat", "batter": SAMPLE_PLAYER, "by": "type"}),
    ("impact board", "/api/slice", {"role": "bowl", "league": "IPL", "first": 2025, "last": 2025,
                                    "by": "player", "sort": "waa"}),
    ("question", "/api/ask", {"q": "best death bowlers IPL 2025"}),
]


def _folder_bytes(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) if path.exists() else 0


def build_times() -> dict:
    """Rebuild from downloaded files, timing ingest and each build step, in seconds."""
    from .cli import BUILD_STEPS
    from .db import rebuild
    from .ingest import cricsheet, styles
    times = {}
    started = time.perf_counter()
    with rebuild(fresh=True) as con:
        for name, step in [("cricket data", cricsheet.ingest), ("playing styles", styles.ingest)]:
            began = time.perf_counter()
            step(con, False)
            times[name] = round(time.perf_counter() - began, 1)
        for name, step in BUILD_STEPS:
            began = time.perf_counter()
            step(con)
            times[name] = round(time.perf_counter() - began, 1)
    times["total"] = round(time.perf_counter() - started, 1)
    return times


def sizes() -> dict:
    """Bytes on disk, and rows in the biggest tables."""
    import duckdb
    con = duckdb.connect(str(DB_PATH), read_only=True)
    rows = con.execute("""select table_name, estimated_size from duckdb_tables()
                          order by estimated_size desc, table_name limit 10""").fetchall()
    matches, balls = con.execute("select (select count(*) from ck_matches), count(*) from ck_ev").fetchone()
    # The ball data alone, as compressed Parquet: the honest size of what we hold.
    parquet = OUT / "balls.parquet"
    OUT.mkdir(parents=True, exist_ok=True)
    con.execute(f"copy ck_events to '{parquet}' (format parquet, compression zstd)")
    parquet_bytes = parquet.stat().st_size
    parquet.unlink()
    con.close()
    return dict(database_bytes=DB_PATH.stat().st_size, raw_bytes=_folder_bytes(RAW),
                balls_parquet_bytes=parquet_bytes,
                lake_bytes=_folder_bytes(DATA / "lake"), matches=matches, balls=balls,
                biggest_tables={name: count for name, count in rows})


def latencies() -> list[dict]:
    """Each endpoint once cold, then WARM_CALLS times: milliseconds and response size."""
    from fastapi.testclient import TestClient

    from .web.app import app
    from .web.db import q
    match = q("""select match_id from matches where league = 'IPL'
                 order by date desc, match_id desc limit 1""")[0]["match_id"]
    client = TestClient(app)
    results = []
    for name, path, params in ENDPOINTS:
        url = path.format(match=match)
        timings = []
        size = 0
        for _ in range(WARM_CALLS + 1):
            began = time.perf_counter()
            reply = client.get(url, params=params)
            timings.append((time.perf_counter() - began) * 1000)
            reply.raise_for_status()
            size = len(reply.content)
        warm = sorted(timings[1:])
        results.append(dict(name=name, cold_ms=round(timings[0], 1),
                            median_ms=round(statistics.median(warm), 1),
                            p95_ms=round(warm[int(0.95 * (len(warm) - 1))], 1),
                            response_bytes=size))
    return results


def run(rebuild_too: bool = True) -> Path:
    report = dict(date=date.today().isoformat(),
                  build_seconds=build_times() if rebuild_too else None,
                  sizes=sizes(), api=latencies())
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{report['date']}.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    return path


# ---- a frozen baseline, and comparing two builds ----

BASELINE = DATA / "baseline"
FLOAT_PLACES = 9   # floats from multi-threaded sums may differ in the last digits


def snapshot(name: str) -> Path:
    """Copy the raw downloads and the database into data/baseline/<name>, with a hash of
    every file, so later builds can be compared with exactly this one."""
    import hashlib
    import shutil
    target = BASELINE / name
    if target.exists():
        raise FileExistsError(f"{target} exists; a baseline is never overwritten")
    shutil.copytree(RAW, target / "raw")
    shutil.copy2(DB_PATH, target / DB_PATH.name)
    hashes = {}
    for path in sorted(p for p in target.rglob("*") if p.is_file()):
        digest = hashlib.sha256()
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(1 << 20), b""):
                digest.update(block)
        hashes[str(path.relative_to(target))] = digest.hexdigest()
    (target / "hashes.json").write_text(json.dumps(hashes, indent=1) + "\n")
    return target


def compare(old: Path, new: Path) -> dict:
    """Table by table: equal, or how they differ, with row order ignored.

    Every column that is not a float must match row for row. Floats are summed in a
    different order by parallel threads, so their last digit can move, and rounding only
    moves the edge where that shows. So each float column is judged by its total and its
    sum of squares, against RELATIVE of the column's size (the sum of its absolute values),
    so a column that sums to nearly zero is judged fairly. On 6.6 million balls the real
    noise is about 1e-8 runs; RELATIVE allows about 1e-5."""
    import duckdb
    con = duckdb.connect()
    con.execute(f"attach '{old}' as a (read_only)")
    con.execute(f"attach '{new}' as b (read_only)")

    def tables(db: str) -> set[str]:
        rows = con.execute("select table_name from duckdb_tables() where database_name = ?", [db])
        return {row[0] for row in rows.fetchall()}

    old_tables, new_tables = tables("a"), tables("b")
    report = dict(only_old=sorted(old_tables - new_tables), only_new=sorted(new_tables - old_tables),
                  equal=[], differ={})
    for table in sorted(old_tables & new_tables):
        problem = _compare_table(con, table)
        if problem:
            report["differ"][table] = problem
        else:
            report["equal"].append(table)
    return report


RELATIVE = 1e-12


def _compare_table(con, table: str) -> str | None:
    """None if the two copies of `table` agree, else what differs."""
    columns = con.execute(f"select column_name, column_type from (describe a.{table})").fetchall()
    if columns != con.execute(f"select column_name, column_type from (describe b.{table})").fetchall():
        return "columns differ"
    exact = [f'"{name}"' for name, kind in columns if kind not in ("DOUBLE", "FLOAT")]
    floats = [name for name, kind in columns if kind in ("DOUBLE", "FLOAT")]
    if exact:
        cols = ", ".join(exact)
        only = "select count(*) from (select {c} from {x}.{t} except all select {c} from {y}.{t})"
        missing, extra = con.execute(
            f"select ({only.format(c=cols, x='a', y='b', t=table)}), "
            f"({only.format(c=cols, x='b', y='a', t=table)})").fetchone()
        if missing or extra:
            return f"{missing} rows only in old, {extra} only in new"
    for name in floats:
        sums = f'sum("{name}"), sum("{name}" * "{name}"), sum(abs("{name}")), count("{name}")'
        total, squares, size, count = con.execute(f"select {sums} from a.{table}").fetchone()
        total2, squares2, _, count2 = con.execute(f"select {sums} from b.{table}").fetchone()
        if count != count2:
            return f"float column {name}: {count} values vs {count2}"
        if count and (abs(total - total2) > RELATIVE * size or abs(squares - squares2) > RELATIVE * squares):
            return f"float column {name} differs: total {total} vs {total2}, squares {squares} vs {squares2}"
    return None
