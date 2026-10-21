"""Reading the scorer's output back as the build writes it, to compare the two."""
from __future__ import annotations

from collections.abc import Iterable


def after_each_ball(records: Iterable[dict]) -> dict[tuple[str, int], float]:
    """Team one's chance once each ball has settled, by (match, ball number).

    A ball settles when the next ball arrives. Until then an innings starting or the match
    ending still changes what that ball led to, which is how the build counts it too.
    """
    settled: dict[tuple[str, int], float] = {}
    open_ball: dict[str, tuple[int, float]] = {}   # match -> (ball number, chance so far)
    for record in records:
        match_id, kind = record["match_id"], record["kind"]
        if kind == "start":
            continue
        if match_id in open_ball:
            seq, chance = open_ball.pop(match_id)
            if kind == "ball":
                settled[match_id, seq] = chance
            elif kind == "innings":
                open_ball[match_id] = (seq, record["wp1"])
            else:
                settled[match_id, seq] = record["wp1"]
        if kind == "ball":
            open_ball[match_id] = (record["seq"], record["wp1"])
    return settled
