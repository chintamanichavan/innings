"""What every sport's model shares.

A sport adapter gives each play two numbers for the batting side:

    ev_pre, ev_post   runs still expected, before and after the play
    wp_pre            the batting side's chance of winning, before the play

From those come the two currencies that work in every sport:

    rae = runs + ev_post - ev_pre    runs above expected
    wpa = wp_post - wp_pre           win probability added
"""
from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss


def add_wpa(plays: pd.DataFrame) -> pd.DataFrame:
    """Turn each play's `wp_pre` into the win chance after it, and the change.

    Needs match_id, seq, bat_team, team1, winner and wp_pre. Adds:
        wp1       team1's chance before the play
        wp1_post  team1's chance after it; after the last play, the real result
        wpa       the change, from the batting side's point of view
    """
    plays = plays.sort_values(["match_id", "seq"], kind="stable").reset_index(drop=True)
    team1_batting = (plays["bat_team"] == plays["team1"]).to_numpy()
    wp1 = np.where(team1_batting, plays["wp_pre"], 1 - plays["wp_pre"])

    # The chance after a play is the chance before the next one. A match with no winner ends at a half.
    result = np.where(plays["winner"].isna(), 0.5, (plays["winner"] == plays["team1"]).astype(float))
    last_play_of_match = (plays["match_id"] != plays["match_id"].shift(-1)).to_numpy()
    wp1_post = np.where(last_play_of_match, result, np.roll(wp1, -1))

    plays["wp1"] = wp1
    plays["wp1_post"] = wp1_post
    plays["wpa"] = np.where(team1_batting, 1, -1) * (wp1_post - wp1)
    return plays


def classifier_scores(outcomes, chances) -> dict:
    """How good a set of stated chances was: sample size, accuracy, log loss and Brier score."""
    chances = np.clip(np.asarray(chances, dtype=float), 1e-6, 1 - 1e-6)
    outcomes = np.asarray(outcomes, dtype=int)
    return {
        "n": int(len(outcomes)),
        "accuracy": float(((chances > 0.5) == (outcomes == 1)).mean()),
        "log_loss": float(log_loss(outcomes, chances, labels=[0, 1])),
        "brier": float(brier_score_loss(outcomes, chances)),
    }


def save_scores(con: duckdb.DuckDBPyConnection, sport: str, model: str, tested_on: str, scores: dict) -> None:
    """Record a model's held-out scores, replacing any earlier run of the same test."""
    con.execute("""
        create table if not exists model_metrics (
            sport varchar, model varchar, split varchar, metric varchar, value double)
    """)
    con.execute("delete from model_metrics where sport = ? and model = ? and split = ?",
                [sport, model, tested_on])
    rows = [(sport, model, tested_on, name, float(value)) for name, value in scores.items()]
    con.executemany("insert into model_metrics values (?, ?, ?, ?, ?)", rows)


def write_table(con: duckdb.DuckDBPyConnection, name: str, frame: pd.DataFrame) -> None:
    """Replace a table with the contents of a data frame."""
    con.register("_frame", frame)
    con.execute(f"create or replace table {name} as select * from _frame")
    con.unregister("_frame")


def attach_values(con: duckdb.DuckDBPyConnection, events: str, valued: str, values: pd.DataFrame,
                  match_columns: str = "", matches: str = "") -> None:
    """Write `valued`: every row of `events` joined to its model values by (match_id, seq).

    `match_columns` adds columns from the `matches` table, such as "m.format as fmt".
    """
    join_matches = f"join {matches} m using (match_id)" if matches else ""
    extra = f", {match_columns}" if match_columns else ""
    con.register("_values", values)
    con.execute(f"""
        create or replace table {valued} as
        select e.*{extra}, v.* exclude (match_id, seq)
        from {events} e {join_matches} join _values v using (match_id, seq)
    """)
    con.unregister("_values")
