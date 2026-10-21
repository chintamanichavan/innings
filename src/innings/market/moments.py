"""Where a match stood at each moment the market priced it."""
from __future__ import annotations

import pandas as pd

T20_BALLS = 120

# moment -> (innings, balls bowled in it). "After four overs" is the state before the first
# ball of the fifth; the end of the first innings is the state before the chase's first ball.
WHEN = {
    "FIRST_INN_FOUR_OV": (1, 24), "FIRST_INN_SIX_OV": (1, 36), "FIRST_INN_TEN_OV": (1, 60),
    "FIRST_INN_FIFTEEN_OV": (1, 90), "FIRST_INN_CONCLUSION": (2, 0),
    "SECOND_INN_FOUR_OV": (2, 24), "SECOND_INN_SIX_OV": (2, 36), "SECOND_INN_TEN_OV": (2, 60),
    "SECOND_INN_FIFTEEN_OV": (2, 90),
}


def states(balls: pd.DataFrame) -> pd.DataFrame:
    """For each match and moment, the first ball bowled at or after it.

    `balls` has match_id, seq, innings and balls_left_pre. A moment the match never reached
    (the innings ended first) has no row.
    """
    rows = []
    for moment, (innings, bowled) in WHEN.items():
        these = balls[(balls["innings"] == innings) & (balls["balls_left_pre"] <= T20_BALLS - bowled)]
        first = these.sort_values(["match_id", "seq"]).groupby("match_id", sort=False).head(1)
        rows.append(first.assign(moment=moment))
    return pd.concat(rows, ignore_index=True)
