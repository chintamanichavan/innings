"""Read-only access to the built database.

The refresher swaps in a new database file while the server is running. `q` notices
the swap and reopens the file, so no caller ever holds a stale handle. `per_database`
is a cache with the same lifetime: it empties itself when the file changes.
"""
from __future__ import annotations

import functools

import duckdb

from ..config import DB_PATH

_con: duckdb.DuckDBPyConnection | None = None
_stamp: tuple | None = None


def stamp() -> tuple:
    """Identifies the database file now on disk. Changes when a rebuild lands."""
    st = DB_PATH.stat()
    return (st.st_ino, st.st_mtime_ns)


def _connection() -> duckdb.DuckDBPyConnection:
    global _con, _stamp
    now = stamp()
    if _con is None or now != _stamp:
        if _con is not None:
            _con.close()
        _con, _stamp = duckdb.connect(str(DB_PATH), read_only=True), now
    return _con


def q(sql: str, params: list | None = None) -> list[dict]:
    """Run one query and return its rows as dicts."""
    cur = _connection().cursor()
    cur.execute(sql, params or [])
    names = [d[0] for d in cur.description]
    return [dict(zip(names, row, strict=True)) for row in cur.fetchall()]


def per_database(max_entries: int = 512):
    """Cache a function's results until the database is rebuilt."""
    def wrap(fn):
        cache: dict = {}
        seen: list = [None]

        @functools.wraps(fn)
        def cached(*args):
            now = stamp()
            if now != seen[0] or len(cache) >= max_entries:
                cache.clear()
                seen[0] = now
            if args not in cache:
                cache[args] = fn(*args)
            return cache[args]
        return cached
    return wrap
