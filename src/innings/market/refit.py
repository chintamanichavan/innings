"""The model's chances for the study's matches, from models that never saw them.

The chances stored in Innings come from models fitted on every match. Here each Big Bash season
gets models fitted afresh on matches before its first day, so nothing is learned from the matches
being scored, or from anything after them.
"""
from __future__ import annotations

import datetime as dt

import duckdb
import numpy as np
import pandas as pd

from ..config import CK_BALLS
from ..models import cricket, predict
from ..models.cricket_limited import ExpectedRuns, _new_win_model, _win_inputs


def t20_balls(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Every T20 ball, as the build's models see it, with its match's date."""
    balls = cricket._load_balls(con)
    competitions = sorted(balls["competition"].unique())
    balls["comp_code"] = balls["competition"].map({name: code for code, name in enumerate(competitions)})
    balls = balls[balls["format"] == "T20"]
    dates = con.execute("select match_id, date from ck_matches").df()
    dates["date"] = pd.to_datetime(dates["date"]).dt.date
    return balls.merge(dates, on="match_id")


def in_play(balls: pd.DataFrame, states: pd.DataFrame, before: dt.date) -> np.ndarray:
    """The batting side's chance in each of `states`, from models fitted on balls before `before`."""
    past = balls[balls["date"] < before]
    expected = ExpectedRuns(past)
    decided = past[past["clean"]]
    won = (decided["bat_team"] == decided["winner"]).astype(int)

    def inputs(frame: pd.DataFrame) -> pd.DataFrame:
        runs_left = expected.at(frame["balls_left_pre"], frame["wkts_pre"], frame)
        par = expected.at(np.full(len(frame), CK_BALLS["T20"]),
                          np.zeros(len(frame), dtype=int), frame)
        return _win_inputs(frame, runs_left, par)

    chances = np.full(len(states), 0.5)
    past_inputs = inputs(decided)
    state_inputs = inputs(states)
    for innings in (1, 2):
        train = (decided["innings"] == innings).to_numpy()
        model = _new_win_model().fit(past_inputs[train], won[train])
        these = (states["innings"] == innings).to_numpy()
        if these.any():
            chances[these] = model.predict_proba(state_inputs[these])[:, 1]
    return chances


def pre_match(con: duckdb.DuckDBPyConnection, starts: dict[str, dt.date],
              match_ids: dict[str, list[str]]) -> pd.DataFrame:
    """The side batting first's chance before each listed match, one season at a time.

    Ratings come from the build's single pass through history, which uses only matches before
    each one. The model that turns ratings into a chance is fitted on matches before the season.
    """
    matches = predict._load_matches(con, "ck")
    history = predict.walk("ck", matches, predict._load_lineups(con, "ck"),
                           predict._load_player_values(con, "ck"))
    decided = predict._decided_matches(matches, history.features)
    features = matches.merge(history.features, on="match_id")
    out = []
    for season, start in starts.items():
        past = decided[decided["date"] < start]
        model = predict._new_model().fit(past[predict.FEATURES], past["y"])
        these = features[features["match_id"].isin(match_ids[season])]
        out.append(pd.DataFrame({"match_id": these["match_id"].to_numpy(),
                                 "p_first": model.predict_proba(these[predict.FEATURES])[:, 1]}))
    return pd.concat(out, ignore_index=True)
