"""Running the trained network, without PyTorch.

The exported model is a file that onnxruntime can run on a CPU in well under a millisecond a
ball. That makes two things cheap enough to do on request: asking what the network expects
from one batter against one bowler, and letting it play out the rest of an innings hundreds
of times.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np

from ..config import DATA
from .features import (
    BALLS_SCALE,
    FORMATS,
    HISTORY,
    OUTCOME_IS_LEGAL,
    OUTCOME_RUNS,
    OUTCOMES,
    PAD,
    UNKNOWN,
    WICKET,
    numeric_matrix,
)

FOLDER = DATA / "nn"
LIMITED = ("T20", "ODI")          # formats with a ball limit, which a simulation needs
BOWLERS_SHARING = 5               # a side uses about five bowlers, so each bowls a fifth of the balls
WIDE = OUTCOMES.index("wide")


def available(folder: Path = FOLDER) -> bool:
    return (folder / "model.onnx").exists()


class Network:
    """The exported model and the ids it knows."""

    def __init__(self, folder: Path = FOLDER):
        import onnxruntime  # imported here so that importing this module is cheap

        options = onnxruntime.SessionOptions()
        options.intra_op_num_threads = 2
        self.session = onnxruntime.InferenceSession(str(folder / "model.onnx"), options,
                                                    providers=["CPUExecutionProvider"])
        self.vocabulary = json.loads((folder / "vocabulary.json").read_text())

    def id_of(self, kind: str, key: str | None) -> int:
        """The network's id for a player, ground or league. Unknown ones share one id."""
        return self.vocabulary[kind].get(key, UNKNOWN) if key else UNKNOWN

    def predict(self, numeric, history, batter, bowler, venue, league, fmt) -> tuple[np.ndarray, np.ndarray]:
        """Outcome and result probabilities for a batch of balls."""
        feeds = dict(numeric=np.asarray(numeric, dtype=np.float32),
                     history=np.asarray(history, dtype=np.int64))
        for name, ids in (("batter", batter), ("bowler", bowler), ("venue", venue), ("league", league),
                          ("fmt", fmt)):
            feeds[name] = np.asarray(ids, dtype=np.int64)
        outcome, result = self.session.run(None, feeds)
        return outcome, result


@lru_cache(maxsize=1)
def network() -> Network:
    return Network()


@dataclass
class Scenario:
    """Where an innings stands, and who is involved. Ids are the network's own."""
    fmt: str
    balls_bowled: int = 0
    wickets: int = 0
    score: int = 0
    target: int | None = None      # runs needed to win, when chasing
    year: int = 2025
    women: bool = False
    league: str | None = None      # the league's name, such as "IPL"
    venue: int = UNKNOWN
    striker: int = UNKNOWN
    non_striker: int = UNKNOWN
    bowler: int = UNKNOWN          # bowls the rest of the current over; after that, an average bowler
    striker_runs: int = 0
    striker_balls: int = 0
    history: list[int] = field(default_factory=list)   # outcomes of the latest balls, oldest first


def _state_inputs(scenario: Scenario, n: int, *, balls, wickets, score, batter_runs,
                  batter_balls) -> np.ndarray:
    fmt = np.full(n, scenario.fmt)
    target = np.full(n, np.nan if scenario.target is None else float(scenario.target))
    return numeric_matrix(
        fmt=fmt, innings=np.full(n, 2 if scenario.target is not None else 1),
        balls_bowled=balls, wickets=wickets, score=score, target=target,
        lead=np.zeros(n), match_balls=np.zeros(n), year=np.full(n, scenario.year),
        women=np.full(n, scenario.women), batter_runs=batter_runs, batter_balls=batter_balls,
        bowler_balls=np.minimum(balls / BOWLERS_SHARING, BALLS_SCALE[scenario.fmt] / BOWLERS_SHARING),
        over=balls // 6,
    )


def _history_row(scenario: Scenario) -> np.ndarray:
    recent = scenario.history[-HISTORY:]
    return np.array([PAD] * (HISTORY - len(recent)) + recent, dtype=np.int64)


def next_ball(net: Network, scenario: Scenario) -> np.ndarray:
    """The chance of each outcome on the next ball of a scenario."""
    numeric = _state_inputs(
        scenario, 1, balls=np.array([scenario.balls_bowled]), wickets=np.array([scenario.wickets]),
        score=np.array([scenario.score]), batter_runs=np.array([scenario.striker_runs]),
        batter_balls=np.array([scenario.striker_balls]))
    one = np.ones(1, dtype=np.int64)
    outcome, _ = net.predict(numeric, _history_row(scenario)[None, :], scenario.striker * one,
                             scenario.bowler * one, scenario.venue * one,
                             net.id_of("leagues", scenario.league) * one,
                             FORMATS.index(scenario.fmt) * one)
    return outcome[0]


def simulate(net: Network, scenario: Scenario, runs: int = 300, seed: int = 0) -> dict:
    """Let the network play out the rest of an innings `runs` times, ball by ball.

    Each simulated innings draws every ball from the network's own probabilities, updates the
    score, and stops when the balls run out, ten wickets fall, or the target is reached.
    Returns `by_ball`, each innings' score after every legal ball (-1 where it was never
    reached), and how each one ended: `score`, `wickets`, `balls` and `reached` (the target).
    """
    if scenario.fmt not in LIMITED:
        raise ValueError("only limited-overs innings can be simulated")
    limit = int(BALLS_SCALE[scenario.fmt])
    random = np.random.default_rng(seed)
    fmt_id = np.full(runs, FORMATS.index(scenario.fmt), dtype=np.int64)
    venue = np.full(runs, scenario.venue, dtype=np.int64)
    league = np.full(runs, net.id_of("leagues", scenario.league), dtype=np.int64)

    balls = np.full(runs, scenario.balls_bowled)
    wickets = np.full(runs, scenario.wickets)
    score = np.full(runs, scenario.score)
    history = np.tile(_history_row(scenario), (runs, 1))
    # Two batters are in. Column 0 is on strike.
    batter_id = np.tile(np.array([scenario.striker, scenario.non_striker], dtype=np.int64), (runs, 1))
    batter_runs = np.tile(np.array([scenario.striker_runs, 0]), (runs, 1))
    batter_balls = np.tile(np.array([scenario.striker_balls, 0]), (runs, 1))
    first_over_ends = (scenario.balls_bowled // 6 + 1) * 6

    def finished() -> np.ndarray:
        reached = score >= scenario.target if scenario.target is not None else np.zeros(runs, dtype=bool)
        return (balls >= limit) | (wickets >= 10) | reached

    # The score when each legal ball has been bowled. Column b is "after b balls of the innings".
    by_ball = np.full((runs, limit + 1), -1)
    by_ball[:, scenario.balls_bowled] = scenario.score
    for _ in range(4 * limit):   # wides do not use up a ball, so allow more steps than balls
        live = ~finished()
        if not live.any():
            break
        bowler = np.where(balls < first_over_ends, scenario.bowler, UNKNOWN).astype(np.int64)
        numeric = _state_inputs(scenario, runs, balls=balls, wickets=wickets, score=score,
                                batter_runs=batter_runs[:, 0], batter_balls=batter_balls[:, 0])
        chances, _ = net.predict(numeric, history, batter_id[:, 0], bowler, venue, league, fmt_id)
        # Draw one outcome per innings from its own probabilities.
        drawn = (chances.cumsum(axis=1) > random.random((runs, 1))).argmax(axis=1)
        drawn = np.where(live, drawn, PAD)
        happened = np.where(live, drawn, 0)

        added = np.where(live, OUTCOME_RUNS[happened], 0)
        legal = live & (OUTCOME_IS_LEGAL[happened] == 1)
        out = live & (happened == WICKET)
        score = score + added
        balls = balls + legal
        wickets = wickets + out
        history = np.where(live[:, None], np.column_stack([history[:, 1:], happened]), history)

        faced = live & (happened != WIDE)
        off_the_bat = np.where(faced & (happened < WICKET), OUTCOME_RUNS[happened], 0)
        batter_runs[:, 0] += off_the_bat
        batter_balls[:, 0] += faced
        # A dismissed batter is replaced by one the network knows nothing about.
        batter_id[out, 0], batter_runs[out, 0], batter_balls[out, 0] = UNKNOWN, 0, 0
        # The batters cross on an odd number of runs, and again when the over ends.
        swap = (faced & (off_the_bat % 2 == 1)) ^ (legal & (balls % 6 == 0))
        for array in (batter_id, batter_runs, batter_balls):
            array[swap] = array[swap][:, ::-1]
        by_ball[np.arange(runs), np.minimum(balls, limit)] = score

    reached = score >= scenario.target if scenario.target is not None else np.zeros(runs, dtype=bool)
    return dict(by_ball=by_ball, score=score, wickets=wickets, balls=balls, reached=reached)
