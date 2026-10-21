"""One simulated match as it travels through Kafka: a fixed-size block of bytes.

A JSON message per ball would be about two billion messages. Instead a match is one message:
a few header bytes, then one byte for what each delivery was and one for who faced it.
Every message is the same size, so a reader can lay thousands of them side by side and
unpack them all at once with no loop.
"""
from __future__ import annotations

import numpy as np

MOST_DELIVERIES = 180   # 120 balls and up to 60 wides and no-balls; no real innings has gone near it

RECORD = np.dtype([
    ("season", "<u4"),
    ("match", "u1"),        # 0-69 the league, then Qualifier 1, Eliminator, Qualifier 2, Final
    ("home", "u1"),         # team numbers
    ("away", "u1"),
    ("first", "u1"),        # which side batted first: 0 home, 1 away
    ("winner", "u1"),       # which side won
    ("outcomes", "u1", (2, MOST_DELIVERIES)),   # by innings; PAD where no ball was bowled
    ("strikers", "u1", (2, MOST_DELIVERIES)),   # the facing batter's place in the batting order
])
THE_END = 0xFFFFFFFF   # a record with this season number says: nothing more is coming


def unpack(payloads: list[bytes]) -> np.ndarray:
    """Many messages -> one array of records."""
    return np.frombuffer(b"".join(payloads), dtype=RECORD)


def end_marker() -> bytes:
    marker = np.zeros(1, dtype=RECORD)
    marker["season"] = THE_END
    return marker.tobytes()
