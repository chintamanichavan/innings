"""T20 and ODI cricket. A side has two resources, balls and wickets, and a chase has a target."""
from __future__ import annotations

import os
from dataclasses import dataclass

import duckdb
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

from ..config import CK_BALLS, DATA
from .common import classifier_scores, save_scores

GRID_COLUMNS = 20   # the expected-runs table shows this many steps of balls left
MODEL_FOLDER = DATA / "models"


class ExpectedRuns:
    """Runs a side can still expect, from balls left and wickets down.

    Learned from complete first innings only: a chase stops when it reaches the target, so its
    totals would understate what the same balls and wickets are worth.
    """

    FEATURES = ["balls_left", "wkts", "year", "comp_code", "female"]

    def __init__(self, balls: pd.DataFrame):
        first_innings = balls["innings"] == 1
        complete = balls["clean"] & balls["full_innings"].fillna(False)
        sample = balls[first_innings & complete]
        # More balls can only mean more runs; more wickets down can only mean fewer.
        self.model = HistGradientBoostingRegressor(
            max_iter=400, learning_rate=0.08, max_leaf_nodes=31, min_samples_leaf=300,
            monotonic_cst=[1, -1, 0, 0, 0], categorical_features=[3], random_state=0,
        ).fit(self._inputs(sample["balls_left_pre"], sample["wkts_pre"], sample), sample["runs_rest"])

    @staticmethod
    def _inputs(balls_left, wickets, context: pd.DataFrame) -> pd.DataFrame:
        """Model inputs for some states, taking year, competition and gender from `context`."""
        return pd.DataFrame({
            "balls_left": np.asarray(balls_left), "wkts": np.asarray(wickets),
            "year": context["year"].to_numpy(), "comp_code": context["comp_code"].to_numpy(),
            "female": context["female"].to_numpy(),
        })

    def at(self, balls_left, wickets, context: pd.DataFrame) -> np.ndarray:
        return np.maximum(self.model.predict(self._inputs(balls_left, wickets, context)), 0)


def _new_win_model() -> HistGradientBoostingClassifier:
    # Inputs are (balls left, wickets down, runs needed, edge). More wickets down can only hurt;
    # a bigger edge can only help.
    return HistGradientBoostingClassifier(
        max_iter=300, learning_rate=0.08, max_leaf_nodes=31, min_samples_leaf=300,
        monotonic_cst=[0, -1, 0, 1], random_state=0,
    )


def _win_inputs(balls: pd.DataFrame, expected: np.ndarray, par: np.ndarray) -> pd.DataFrame:
    """What the win model sees. `edge` is how far ahead of the game the batting side is:
    batting first, projected total minus par; chasing, expected runs minus runs needed."""
    chasing = (balls["innings"] == 2).to_numpy()
    needed = (balls["target"] - balls["score_pre"]).to_numpy(dtype=float)
    return pd.DataFrame({
        "balls_left": balls["balls_left_pre"].to_numpy(),
        "wkts": balls["wkts_pre"].to_numpy(),
        "need": np.where(chasing, needed, 0.0),
        "edge": np.where(chasing, expected - needed, balls["score_pre"] + expected - par),
    }, index=balls.index)


def _win_chances(con: duckdb.DuckDBPyConnection, balls: pd.DataFrame, inputs: pd.DataFrame,
                 fmt: str) -> tuple[pd.Series, dict]:
    """The batting side's chance before each ball, and the model for each innings that gave it."""
    batting_side_won = (balls["bat_team"] == balls["winner"]).astype(int)
    decided = balls["clean"].to_numpy()
    held_out_from = int(balls["year"].max()) - 1   # the last full year and the current one
    recent = (balls["year"] >= held_out_from).to_numpy()

    chances = pd.Series(0.5, index=balls.index)
    models = {}
    held_out_outcomes, held_out_chances = [], []
    for innings in (1, 2):
        this_innings = (balls["innings"] == innings).to_numpy()
        earlier, held_out = this_innings & decided & ~recent, this_innings & decided & recent

        trial = _new_win_model().fit(inputs[earlier], batting_side_won[earlier])
        held_out_outcomes.append(batting_side_won[held_out])
        held_out_chances.append(trial.predict_proba(inputs[held_out])[:, 1])

        kept = _new_win_model().fit(inputs[this_innings & decided], batting_side_won[this_innings & decided])
        chances[this_innings] = kept.predict_proba(inputs[this_innings])[:, 1]
        models[innings] = kept

    save_scores(con, "ck", f"win_prob:{fmt}", f"holdout {held_out_from}+",
                classifier_scores(np.concatenate(held_out_outcomes), np.concatenate(held_out_chances)))
    return chances, models


@dataclass
class Saved:
    """One format's models, kept on disk so a ball can be valued away from the build."""

    fmt: str
    expected: ExpectedRuns
    win: dict[int, HistGradientBoostingClassifier]   # by innings
    competitions: list[str]                          # a competition's code is its place here

    def win_chance(self, states: pd.DataFrame) -> np.ndarray:
        """The batting side's chance in each state.

        `states` has the columns of a ball before it is bowled: innings, score_pre, wkts_pre,
        balls_left_pre, target, year, comp_code and female.
        """
        expected = self.expected.at(states["balls_left_pre"], states["wkts_pre"], states)
        full = np.full(len(states), CK_BALLS[self.fmt])
        par = self.expected.at(full, np.zeros(len(states), dtype=int), states)
        inputs = _win_inputs(states, expected, par)
        chances = np.full(len(states), 0.5)
        for innings, model in self.win.items():
            these = (states["innings"] == innings).to_numpy()
            if these.any():
                chances[these] = model.predict_proba(inputs[these])[:, 1]
        return chances

    def save(self) -> None:
        MODEL_FOLDER.mkdir(parents=True, exist_ok=True)
        unfinished = MODEL_FOLDER / f"{self.fmt}.writing"
        joblib.dump(self, unfinished)
        os.replace(unfinished, MODEL_FOLDER / f"{self.fmt}.joblib")   # never a half-written file


def load(fmt: str) -> Saved:
    return joblib.load(MODEL_FOLDER / f"{fmt}.joblib")


def _expected_runs_grid(expected: ExpectedRuns, balls: pd.DataFrame, fmt: str,
                        competitions: list[str]) -> list[tuple]:
    """Expected runs by (balls left, wickets down) for each competition: latest year, men."""
    full_innings = CK_BALLS[fmt]
    year = int(balls["year"].max())
    states = pd.DataFrame(
        [(balls_left, wickets)
         for wickets in range(10)
         for balls_left in range(full_innings, 0, -full_innings // GRID_COLUMNS)],
        columns=["balls_left", "wickets"])
    grid = []
    for competition in sorted(balls["competition"].unique()):
        context = pd.DataFrame(
            {"year": year, "comp_code": competitions.index(competition), "female": 0}, index=states.index)
        runs = expected.at(states["balls_left"], states["wickets"], context)
        grid += [(competition, int(b), int(w), float(r))
                 for b, w, r in zip(states["balls_left"], states["wickets"], runs, strict=True)]
    return grid


def value(con: duckdb.DuckDBPyConnection, balls: pd.DataFrame, fmt: str,
          competitions: list[str]) -> tuple[pd.DataFrame, list[tuple]]:
    """Expected runs before and after each ball, and the win chance before it.

    Returns the three columns indexed like `balls`, plus the rows of the expected-runs grid.
    """
    expected = ExpectedRuns(balls)

    legal = ~(balls["wide"] | balls["noball"])
    balls_left_after = balls["balls_left_pre"] - legal.astype(int)
    wickets_after = balls["wkts_pre"] + balls["outs"]
    innings_over = (balls_left_after <= 0) | (wickets_after >= 10)

    before = expected.at(balls["balls_left_pre"], balls["wkts_pre"], balls)
    # The same yardstick in both innings. A chase won early keeps credit for what was left unused.
    after = np.where(
        innings_over, 0.0,
        expected.at(balls_left_after.clip(lower=0), wickets_after.clip(upper=9), balls))
    par = expected.at(np.full(len(balls), CK_BALLS[fmt]), np.zeros(len(balls), dtype=int), balls)

    values = pd.DataFrame({"ev_pre": before, "ev_post": after}, index=balls.index)
    values["wp_pre"], win_models = _win_chances(con, balls, _win_inputs(balls, before, par), fmt)
    Saved(fmt, expected, win_models, competitions).save()
    return values, _expected_runs_grid(expected, balls, fmt, competitions)
