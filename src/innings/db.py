from __future__ import annotations

import os
import shutil
from contextlib import contextmanager
from pathlib import Path

import duckdb

from .config import DB_PATH


def connect(read_only: bool = False, path: Path = DB_PATH) -> duckdb.DuckDBPyConnection:
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path), read_only=read_only)


@contextmanager
def rebuild(fresh: bool):
    """Write to a side file and swap it in at the end, so a running server never sees
    a half-built database. fresh=False starts from a copy of the current one."""
    work = DB_PATH.with_suffix(".building")
    work.unlink(missing_ok=True)
    if not fresh and DB_PATH.exists():
        shutil.copy(DB_PATH, work)
    con = connect(path=work)
    try:
        yield con
        con.close()
        os.replace(work, DB_PATH)
    finally:
        work.unlink(missing_ok=True)
