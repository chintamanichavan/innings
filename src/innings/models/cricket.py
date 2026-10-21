"""Cricket: value every ball in every format.

T20 and ODI share one model shape, in `cricket_limited`. Tests have their own, in
`cricket_test`. This module loads the balls, hands each format to its model, and turns the
results into credit for batters and bowlers.
"""
from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd

from ..config import CK_BALLS
from . import cricket_limited, cricket_test
from .common import add_wpa, attach_values

VALUE_COLUMNS = ["match_id", "seq", "ev_pre", "ev_post", "rae", "bat_rae", "bowl_rae",
                 "wp_pre", "wp1", "wp1_post", "wpa"]


def _load_balls(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Every ball with its match context and the runs scored from it to the end of its innings."""
    return con.execute("""
        select e.match_id, e.seq, e.innings, e.bat_team, m.team1, m.winner, m.year, m.competition,
               m.format, m.result, m.method, (m.gender = 'female')::int as female,
               m.result = 'win' and m.method is null as clean,
               e.runs, e.runs_bat, e.byes, e.wide, e.noball, e.outs,
               e.score_pre, e.wkts_pre, e.balls_left_pre, e.target,
               e.lead_pre, e.inn_balls_pre, e.match_balls_pre,
               sum(e.runs) over (partition by e.match_id, e.innings order by e.seq
                                 rows between current row and unbounded following) as runs_rest,
               case when e.innings = 1 then m.wkts1 = 10 or m.balls1 = m.max_balls end as full_innings
        from ck_events e join ck_matches m using (match_id)
        order by e.match_id, e.seq
    """).df()


def _add_credit(balls: pd.DataFrame) -> None:
    """Split each ball's value between batter and bowler, then centre it on the league average.

    A wide is the bowler's alone. Byes are nobody's. Extras and scoring rates make the raw
    numbers drift from zero, so each league season is centred: 0 means an average player there.
    """
    change = balls["ev_post"] - balls["ev_pre"]
    balls["rae"] = balls["runs"] + change
    balls["bat_rae"] = np.where(balls["wide"], 0.0, balls["runs_bat"] + change)
    balls["bowl_rae"] = -(balls["runs"] - balls["byes"] + change)

    league_season = [balls["competition"], balls["female"], balls["year"]]
    faced = ~balls["wide"]
    faced_groups = [key[faced] for key in league_season]
    balls.loc[faced, "bat_rae"] -= balls.loc[faced, "bat_rae"].groupby(faced_groups).transform("mean")
    balls["bowl_rae"] -= balls["bowl_rae"].groupby(league_season).transform("mean")


def build(con: duckdb.DuckDBPyConnection) -> None:
    """Write ck_ev (every ball with its values) and ck_er_grid (for the model page)."""
    balls = _load_balls(con)
    competitions = sorted(balls["competition"].unique())
    balls["comp_code"] = balls["competition"].map({name: code for code, name in enumerate(competitions)})

    per_format, grid = [], []
    for fmt in balls["format"].unique():
        these = balls[balls["format"] == fmt]
        if CK_BALLS[fmt] is None:
            values, rows = cricket_test.value(con, these)
        else:
            values, rows = cricket_limited.value(con, these, fmt, competitions)
        per_format.append(values)
        grid += rows
    balls = balls.join(pd.concat(per_format))

    _add_credit(balls)
    balls = add_wpa(balls)
    attach_values(con, "ck_events", "ck_ev", balls[VALUE_COLUMNS],
                  match_columns="m.format as fmt", matches="ck_matches")

    con.execute("""create or replace table ck_er_grid (
        competition varchar, balls_left int, wkts int, er double)""")
    con.executemany("insert into ck_er_grid values (?, ?, ?, ?)", grid)
