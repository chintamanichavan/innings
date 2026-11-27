"""Pace or spin, estimated from how a bowler is used and how his wickets fall.

Wikipedia gives a bowling style for most bowlers, but not for many from smaller nations.
For those, the scorecards still tell a lot: spinners get stumpings and bowl long unbroken
spells in the middle overs and with the old ball; quicks get edges to the keeper, open the
bowling, come back at the death and bowl more no-balls.

A logistic regression learns pace-or-spin from the bowlers whose style we know. Its
accuracy is measured on known bowlers it did not learn from, and an estimate is kept only
when the model is sure (`SURE`) and the bowler has bowled enough (`MIN_BALLS`). Known
styles are never replaced. The exact type (off-spin, leg-spin...) is not estimated.
A boosted-tree model was tried too: no more accurate, and over-sure of its answers.
"""
from __future__ import annotations

import duckdb
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

MIN_BALLS = 60          # fewer balls than this and the scorecard says too little
SURE = 0.9              # the model's chance of its answer must be at least this
FOLDS = 5
PRIOR = 5               # wickets' worth of the average mix, added to every bowler's

# A keeper is anyone who has made a stumping twice: then a catch they take is an edge.
# A spell is a run of overs from one end: the bowler's next over comes two overs later.
FEATURES_SQL = """
with keepers as (
    select fielder_id from ck_ev where dismissal = 'stumped' group by 1 having count(*) >= 2
), overs as (
    select distinct match_id, innings, bowler_id, "over" from ck_ev
), breaks as (
    select bowler_id, coalesce("over" - lag("over") over (
               partition by match_id, innings, bowler_id order by "over") > 2, true) as starts
    from overs
), spells as (
    select bowler_id, count(*) / count(*) filter (where starts) as spell from breaks group by 1
), balls as (
    select e.bowler_id, e.fmt, e."over", e.wide, e.noball, e.bowler_wicket, e.dismissal, e.byes,
           e.runs - e.byes as conceded,
           e.fielder_id in (select fielder_id from keepers) as to_keeper, {phase} as phase
    from ck_ev e
)
select bowler_id, count(*) as n,
       count(*) filter (where bowler_wicket) as wkts,
       count(*) filter (where dismissal = 'stumped') as stumped,
       count(*) filter (where dismissal = 'caught' and to_keeper) as behind,
       count(*) filter (where dismissal in ('bowled', 'lbw')) as bowled_lbw,
       count(*) filter (where dismissal = 'caught and bowled') as own_catch,
       count(*) filter (where fmt <> 'Test') as limited,
       count(*) filter (where phase = 'powerplay') as powerplay,
       count(*) filter (where phase = 'middle') as middle,
       count(*) filter (where phase = 'death') as death,
       count(*) filter (where fmt = 'Test') as test,
       count(*) filter (where phase = 'new-ball') as new_ball,
       count(*) filter (where "over" = 0) as first_over,
       count(*) filter (where wide) as wides,
       count(*) filter (where noball) as noballs,
       sum(byes) as byes, sum(conceded) as conceded, any_value(spell) as spell
from balls join spells using (bowler_id) group by 1 order by 1
"""

WICKET_SHARES = ("stumped", "behind", "bowled_lbw", "own_catch")


def features(rows: list[dict]) -> np.ndarray:
    """One row of numbers per bowler. Shares of wickets are pulled toward the average mix,
    so a bowler with two wickets is not judged on them alone."""
    wkts = np.array([row["wkts"] for row in rows], dtype=float)
    columns = []
    for name in WICKET_SHARES:
        count = np.array([row[name] for row in rows], dtype=float)
        average = count.sum() / max(wkts.sum(), 1)
        columns.append((count + PRIOR * average) / (wkts + PRIOR))
    def share(top: str, bottom: str) -> np.ndarray:
        top_ = np.array([row[top] for row in rows], dtype=float)
        bottom_ = np.array([row[bottom] for row in rows], dtype=float)
        return np.divide(top_, bottom_, out=np.full_like(top_, np.nan), where=bottom_ > 0)
    for top, bottom in (("powerplay", "limited"), ("middle", "limited"), ("death", "limited"),
                        ("new_ball", "test"), ("first_over", "n"), ("wides", "n"), ("noballs", "n"),
                        ("byes", "n"), ("conceded", "n")):
        columns.append(share(top, bottom))
    columns.append(np.array([row["spell"] for row in rows], dtype=float))   # overs in a spell
    table = np.column_stack(columns)
    # A bowler with no Test balls, or none in limited overs, gets the average there.
    means = np.nanmean(table, axis=0)
    return np.where(np.isnan(table), means, table)


def _model():
    return make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))


def estimate(con: duckdb.DuckDBPyConnection, phase_sql: str) -> tuple[dict[str, str], dict]:
    """(bowler id -> "pace" or "spin" for unknown bowlers the model is sure of, a report).

    The report holds the measured accuracy on held-out known bowlers, overall and for the
    sure answers only, and how many unknown bowlers were placed.
    """
    cur = con.execute(FEATURES_SQL.format(phase=phase_sql))
    names = [d[0] for d in cur.description]
    rows = [dict(zip(names, row, strict=True)) for row in cur.fetchall()]
    rows = [row for row in rows if row["n"] >= MIN_BALLS]
    styled = con.execute("select player_id, bowl_type from ck_styles where bowl_type is not null")
    is_pace = {player: kind.endswith("pace") for player, kind in styled.fetchall()}
    x = features(rows)
    labelled = np.array([row["bowler_id"] in is_pace for row in rows])
    y = np.array([is_pace.get(row["bowler_id"], False) for row in rows])
    report = _held_out(x[labelled], y[labelled])
    model = _model().fit(x[labelled], y[labelled])
    chance_pace = model.predict_proba(x[~labelled])[:, 1]
    unknown = [row["bowler_id"] for row, has in zip(rows, labelled, strict=True) if not has]
    placed = {player: ("pace" if p >= 0.5 else "spin")
              for player, p in zip(unknown, chance_pace, strict=True) if max(p, 1 - p) >= SURE}
    report |= dict(unknown=len(unknown), placed=len(placed))
    return placed, report


def _held_out(x: np.ndarray, y: np.ndarray) -> dict:
    """Accuracy on known bowlers, each judged by a model that never saw them."""
    chance = np.zeros(len(y))
    for train, test in StratifiedKFold(FOLDS, shuffle=True, random_state=0).split(x, y):
        chance[test] = _model().fit(x[train], y[train]).predict_proba(x[test])[:, 1]
    guess = chance >= 0.5
    sure = np.maximum(chance, 1 - chance) >= SURE
    return dict(known=int(len(y)), accuracy=float((guess == y).mean()),
                sure_share=float(sure.mean()), sure_accuracy=float((guess[sure] == y[sure]).mean()))
