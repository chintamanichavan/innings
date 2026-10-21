"""What the network is shown for one ball.

This module has no PyTorch in it. Training and serving both build their inputs here, so the
network sees exactly the same numbers in both places.
"""
from __future__ import annotations

import numpy as np

# ---- what the network predicts ----

OUTCOMES = ["dot", "1", "2", "3", "4", "6", "wicket", "wide", "no-ball"]
RUNS_TO_OUTCOME = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 4, 6: 5, 7: 5}   # the rare 5 and 7 fold into 4 and 6
WICKET, WIDE, NO_BALL = 6, 7, 8
# Runs added to the total by each outcome, and whether it uses up a ball.
OUTCOME_RUNS = np.array([0, 1, 2, 3, 4, 6, 0, 1, 1])
OUTCOME_IS_LEGAL = np.array([1, 1, 1, 1, 1, 1, 1, 0, 0])

RESULTS = ["batting side loses", "no winner", "batting side wins"]

# ---- what the network is shown ----

FORMATS = ["T20", "ODI", "Test"]
HISTORY = 24            # how many earlier balls of the innings it sees
PAD = len(OUTCOMES)     # "there was no ball here": the innings had not started yet
UNKNOWN = 0             # the id shared by every player or ground too rarely seen to learn

NUMERIC = [
    "progress",        # how far through the innings: balls used over balls allowed
    "wickets",         # wickets down, out of ten
    "score",           # innings runs so far, on the format's scale
    "run_rate",        # runs per ball so far
    "chasing",         # 1 when the side is batting to a target
    "need",            # runs still needed, on the format's scale
    "required_rate",   # runs per ball needed
    "lead",            # Test only: batting side's lead across the match
    "match_progress",  # Test only: balls bowled in the match
    "innings_2", "innings_3", "innings_4",
    "year",            # the game changes over time
    "women",
    "batter_runs",     # the striker's innings so far
    "batter_balls",
    "bowler_balls",    # how much this bowler has bowled in the match
    "over_in_ten",     # where in a ten-over block: new ball, middle, end
]

SCORE_SCALE = {"T20": 200.0, "ODI": 300.0, "Test": 400.0}
BALLS_SCALE = {"T20": 120.0, "ODI": 300.0, "Test": 600.0}   # a Test innings has no limit; 100 overs is long


def numeric_matrix(*, fmt, innings, balls_bowled, wickets, score, target, lead, match_balls, year,
                   women, batter_runs, batter_balls, bowler_balls, over) -> np.ndarray:
    """The numeric inputs for many balls at once: one row per ball, columns in the order of NUMERIC.

    Every argument is an array with one value per ball. `fmt` holds format names and `target`
    holds the runs needed to win, or NaN when the side is not chasing. This is the only place
    these numbers are computed: training, single predictions and simulation all come here.
    """
    fmt = np.asarray(fmt)
    balls_allowed = np.vectorize(BALLS_SCALE.get)(fmt).astype(float)
    score_scale = np.vectorize(SCORE_SCALE.get)(fmt).astype(float)
    is_test = fmt == "Test"
    bowled = np.asarray(balls_bowled, dtype=float)
    score = np.asarray(score, dtype=float)
    target = np.asarray(target, dtype=float)
    innings = np.asarray(innings)

    chasing = ~np.isnan(target)
    need = np.where(chasing, np.maximum(np.nan_to_num(target) - score, 0), 0)
    balls_left = np.maximum(balls_allowed - bowled, 1.0)
    columns = [
        np.minimum(bowled / balls_allowed, 1.5),
        np.asarray(wickets) / 10.0,
        score / score_scale,
        np.minimum(score / np.maximum(bowled, 6), 3.0),
        chasing.astype(float),
        need / score_scale,
        np.where(chasing & ~is_test, np.minimum(need / balls_left, 3.0), 0.0),
        np.where(is_test, np.clip(np.asarray(lead) / 300.0, -2.0, 2.0), 0.0),
        np.where(is_test, np.minimum(np.asarray(match_balls) / 2700.0, 1.5), 0.0),
        (innings == 2).astype(float),
        (innings == 3).astype(float),
        (innings >= 4).astype(float),
        (np.asarray(year) - 2015) / 10.0,
        np.asarray(women, dtype=float),
        np.minimum(np.asarray(batter_runs) / 50.0, 4.0),
        np.minimum(np.asarray(batter_balls) / 30.0, 6.0),
        np.minimum(np.asarray(bowler_balls) / 24.0, 6.0),
        (np.asarray(over) % 10) / 10.0,
    ]
    assert len(columns) == len(NUMERIC)
    return np.stack(columns, axis=1).astype(np.float32)
