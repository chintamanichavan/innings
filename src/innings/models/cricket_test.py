"""Test cricket. An innings has no ball limit, a match has four of them, and a draw is a real result."""
from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

from .common import classifier_scores, save_scores

# Inputs to the win and loss models, and which way each may move the chance of WINNING:
# +1 can only help, -1 can only hurt, 0 is free. The loss model uses the opposite signs.
EARLY_INPUTS = {"innings": 0, "lead": 1, "wkts": -1, "match_balls": 0, "ev": 1, "female": 0}
CHASE_INPUTS = {"need": -1, "wkts": -1, "match_balls": 0, "ev": 1}
# There are under a thousand Tests to learn from. Big leaves stop a model memorising single matches.
EARLY_LEAF, CHASE_LEAF = 4000, 600


class ExpectedRuns:
    """Runs still to come in an innings, from wickets down, which innings it is, and balls faced.

    Learned from the first three innings. A fourth-innings chase stops at its target, so its
    totals would understate what the wickets in hand are worth.
    """

    def __init__(self, balls: pd.DataFrame):
        sample = balls[(balls["innings"] <= 3).to_numpy()]
        self.model = HistGradientBoostingRegressor(
            max_iter=300, learning_rate=0.08, max_leaf_nodes=31, min_samples_leaf=500,
            monotonic_cst=[-1, 0, 0, 0, 0], random_state=0,   # more wickets down: fewer runs to come
        ).fit(self._inputs(sample["wkts_pre"], sample["inn_balls_pre"], sample), sample["runs_rest"])

    @staticmethod
    def _inputs(wickets, innings_balls, context: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame({
            "wkts": np.asarray(wickets), "innings": context["innings"].to_numpy(),
            "inn_balls": np.asarray(innings_balls), "year": context["year"].to_numpy(),
            "female": context["female"].to_numpy(),
        })

    def at(self, wickets, innings_balls, context: pd.DataFrame) -> np.ndarray:
        return np.maximum(self.model.predict(self._inputs(wickets, innings_balls, context)), 0)


class ResultModel:
    """The batting side's chance to win and to lose, with a draw as whatever is left.

    Innings one to three share a pair of models. The fourth innings is a chase, so it has its
    own pair built on runs still needed, which lets it see the finish coming.
    """

    def __init__(self, inputs: pd.DataFrame, won: np.ndarray, lost: np.ndarray, rows: np.ndarray):
        self.inputs = inputs
        self.chasing = (inputs["innings"] >= 4).to_numpy()
        self.early = self._fit_pair(EARLY_INPUTS, EARLY_LEAF, rows & ~self.chasing, won, lost)
        self.chase = self._fit_pair(CHASE_INPUTS, CHASE_LEAF, rows & self.chasing, won, lost)

    def _fit_pair(self, directions: dict[str, int], leaf: int, rows: np.ndarray,
                  won: np.ndarray, lost: np.ndarray) -> list[HistGradientBoostingClassifier]:
        columns = list(directions)
        pair = []
        for sign, outcome in ((1, won), (-1, lost)):
            model = HistGradientBoostingClassifier(
                max_iter=150, learning_rate=0.06, max_leaf_nodes=15, min_samples_leaf=leaf,
                monotonic_cst=[sign * direction for direction in directions.values()], random_state=0,
            )
            pair.append(model.fit(self.inputs.loc[rows, columns], outcome[rows]))
        return pair

    def points(self, rows: np.ndarray) -> np.ndarray:
        """Expected result for the batting side on the given rows: a win is 1, a draw a half."""
        points = np.full(int(rows.sum()), 0.5)
        chasing = self.chasing[rows]
        stages = ((self.early, list(EARLY_INPUTS), ~chasing), (self.chase, list(CHASE_INPUTS), chasing))
        for (win_model, loss_model), columns, in_stage in stages:
            if not in_stage.any():
                continue
            states = self.inputs.loc[rows, columns][in_stage]
            p_win = win_model.predict_proba(states)[:, 1]
            p_loss = loss_model.predict_proba(states)[:, 1]
            total = np.maximum(p_win + p_loss, 1.0)   # the two together must leave room for a draw
            points[in_stage] = 0.5 * (1 + (p_win - p_loss) / total)
        return points


def _result_inputs(balls: pd.DataFrame, expected_before: np.ndarray) -> pd.DataFrame:
    """What the result models see. Balls bowled in the match so far stand in for time left."""
    inputs = pd.DataFrame({
        "innings": balls["innings"].to_numpy(), "lead": balls["lead_pre"].to_numpy(),
        "wkts": balls["wkts_pre"].to_numpy(), "match_balls": balls["match_balls_pre"].to_numpy(),
        "ev": expected_before, "female": balls["female"].to_numpy(),
    }, index=balls.index)
    chasing = (balls["innings"] >= 4).to_numpy()
    inputs["need"] = np.where(chasing, -inputs["lead"] + 1, 0)
    return inputs


def _expected_runs_grid(expected: ExpectedRuns, balls: pd.DataFrame) -> list[tuple]:
    """Expected runs at the start of each innings by wickets down: latest year, men.

    The grid table is shared with the limited-overs formats, whose second key is balls left.
    For Tests that key holds the innings number instead.
    """
    states = pd.DataFrame([(wickets, innings) for wickets in range(10) for innings in (1, 2, 3, 4)],
                          columns=["wickets", "innings"])
    context = pd.DataFrame({"innings": states["innings"], "year": int(balls["year"].max()), "female": 0})
    runs = expected.at(states["wickets"], np.zeros(len(states)), context)
    return [("Test", int(innings), int(wickets), float(r))
            for wickets, innings, r in zip(states["wickets"], states["innings"], runs, strict=True)]


def value(con: duckdb.DuckDBPyConnection, balls: pd.DataFrame) -> tuple[pd.DataFrame, list[tuple]]:
    """Expected runs before and after each ball, and the expected result before it."""
    expected = ExpectedRuns(balls)
    legal = ~(balls["wide"] | balls["noball"])
    wickets_after = balls["wkts_pre"] + balls["outs"]
    innings_balls_after = balls["inn_balls_pre"] + legal.astype(int)

    before = expected.at(balls["wkts_pre"], balls["inn_balls_pre"], balls)
    after = np.where(
        wickets_after >= 10, 0.0,
        expected.at(wickets_after.clip(upper=9), innings_balls_after, balls))
    values = pd.DataFrame({"ev_pre": before, "ev_post": after}, index=balls.index)

    inputs = _result_inputs(balls, before)
    won = (balls["bat_team"] == balls["winner"]).to_numpy()
    lost = balls["winner"].notna().to_numpy() & ~won
    finished = balls["result"].isin(["win", "draw", "tie"]).to_numpy() & balls["method"].isna().to_numpy()
    held_out_from = int(balls["year"].max()) - 1   # the last full year and the current one
    recent = (balls["year"] >= held_out_from).to_numpy()

    # Score a model on matches it has not seen. Only decided matches have a side to call right.
    trial = ResultModel(inputs, won, lost, finished & ~recent)
    held_out = finished & recent & (won | lost)
    save_scores(con, "ck", "win_prob:Test", f"holdout {held_out_from}+, decided matches",
                classifier_scores(won[held_out].astype(int), trial.points(held_out)))

    kept = ResultModel(inputs, won, lost, finished)
    values["wp_pre"] = kept.points(np.ones(len(balls), dtype=bool))
    return values, _expected_runs_grid(expected, balls)
