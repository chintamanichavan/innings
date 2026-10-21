"""A cricket match as a scorecard reads it, and as a television broadcast draws it.

One pass over the match's balls gives, for each innings: the batting card, the bowling
card, extras, the fall of wickets, the partnerships, and the runs in each over.
"""
from __future__ import annotations

import pandas as pd
from fastapi import HTTPException

from .db import per_database, q

BALLS_PER_OVER = 6
BOUNDARY_FOUR, BOUNDARY_SIX = 4, 6

# How a scorecard writes each way of getting out. {f} is the fielder, {b} the bowler.
HOW_OUT = {
    "caught": "c {f} b {b}",
    "caught and bowled": "c & b {b}",
    "bowled": "b {b}",
    "lbw": "lbw b {b}",
    "stumped": "st {f} b {b}",
    "hit wicket": "hit wicket b {b}",
    "run out": "run out ({f})",
}


def overs_text(legal_balls: int) -> str:
    """Balls as cricket writes overs: 119 balls is 19.5."""
    overs, balls = divmod(int(legal_balls), BALLS_PER_OVER)
    return f"{overs}.{balls}" if balls else str(overs)


def how_out(kind: str, fielder: str | None, bowler: str) -> str:
    text = HOW_OUT.get(kind, kind).format(f=fielder or "sub", b=bowler)
    return text.replace(" (sub)", "") if fielder is None else text


def _load(match_id: str) -> tuple[pd.DataFrame, dict[str, str]]:
    """Every ball of the match, oldest first, and the name of every player in it."""
    balls = pd.DataFrame(q("select * from ck_events where match_id = ? order by seq", [match_id]))
    if balls.empty:
        raise HTTPException(404, "no balls recorded for this match")
    balls["legal"] = ~(balls["wide"] | balls["noball"])
    # A bowler is charged with everything except byes and leg-byes.
    balls["conceded"] = balls["runs"] - balls["byes"]
    names = {row["player_id"]: row["name"] for row in q(
        """select player_id, name from ck_players where player_id in (
               select player_id from ck_lineups where match_id = ?)""", [match_id])}
    return balls, names


# ---- the cards ----

def _batting(innings: pd.DataFrame, names: dict[str, str]) -> list[dict]:
    """One line per batter, in the order they came to the crease."""
    order = pd.unique(innings[["batter_id", "non_striker_id"]].to_numpy().ravel())
    wickets = innings[innings["outs"] > 0].set_index("dismissed_id")
    card = []
    for batter in order:
        faced = innings[innings["batter_id"] == batter]
        runs, balls = int(faced["runs_bat"].sum()), int((~faced["wide"]).sum())
        line = dict(
            player_id=batter, name=names.get(batter, "Unknown"), runs=runs, balls=balls,
            fours=int((faced["runs_bat"] == BOUNDARY_FOUR).sum()),
            sixes=int((faced["runs_bat"] == BOUNDARY_SIX).sum()),
            strike_rate=100 * runs / balls if balls else None, out=batter in wickets.index, how="not out",
        )
        if line["out"]:
            wicket = wickets.loc[batter]
            line["how"] = how_out(wicket["dismissal"], names.get(wicket["fielder_id"]),
                                   names.get(wicket["bowler_id"], "Unknown"))
        card.append(line)
    return card


def _maidens(spell: pd.DataFrame) -> int:
    """Complete overs in which the bowler gave away nothing."""
    by_over = spell.groupby("over").agg(legal=("legal", "sum"), conceded=("conceded", "sum"))
    return int(((by_over["legal"] == BALLS_PER_OVER) & (by_over["conceded"] == 0)).sum())


def _bowling(innings: pd.DataFrame, names: dict[str, str]) -> list[dict]:
    """One line per bowler, in the order they first bowled."""
    card = []
    for bowler in pd.unique(innings["bowler_id"]):
        spell = innings[innings["bowler_id"] == bowler]
        legal, conceded = int(spell["legal"].sum()), int(spell["conceded"].sum())
        card.append(dict(
            player_id=bowler, name=names.get(bowler, "Unknown"), overs=overs_text(legal),
            maidens=_maidens(spell), runs=conceded, wickets=int(spell["bowler_wicket"].sum()),
            economy=BALLS_PER_OVER * conceded / legal if legal else None,
            wides=int(spell["wide"].sum()), no_balls=int(spell["noball"].sum()),
        ))
    return card


def _extras(innings: pd.DataFrame) -> dict:
    penalty = innings["extras"] - innings["byes"]   # the run a wide or no-ball costs by itself
    return dict(
        total=int(innings["extras"].sum()), byes=int(innings["byes"].sum()),
        wides=int(penalty[innings["wide"]].sum()), no_balls=int(penalty[innings["noball"]].sum()),
    )


# ---- what a broadcast draws ----

def _fall_of_wickets(innings: pd.DataFrame, names: dict[str, str]) -> list[dict]:
    wickets = innings[innings["outs"] > 0]
    first = int(innings["wkts_pre"].iloc[0]) + 1
    return [dict(wicket=number, score=int(ball.score_pre + ball.runs),
                 name=names.get(ball.dismissed_id, "Unknown"), over=f"{ball.over}.{ball.ball}")
            for number, ball in enumerate(wickets.itertuples(), start=first)]


def _partnerships(innings: pd.DataFrame, names: dict[str, str]) -> list[dict]:
    """The runs each pair added, with each batter's share. A stand ends when a wicket falls."""
    stand = innings["outs"].cumsum().shift(fill_value=0)   # the wicket's own ball belongs to the old stand
    pairs = []
    for number, together in innings.groupby(stand):
        batters = pd.unique(together[["batter_id", "non_striker_id"]].to_numpy().ravel())[:2]
        shares = [dict(name=names.get(batter, "Unknown"),
                       runs=int(together.loc[together["batter_id"] == batter, "runs_bat"].sum()))
                  for batter in batters]
        pairs.append(dict(wicket=int(number) + 1, runs=int(together["runs"].sum()),
                          balls=int(together["legal"].sum()), batters=shares))
    return pairs


def _overs(innings: pd.DataFrame) -> list[dict]:
    """Runs and wickets in each over, and the score when it ended: the Manhattan and the worm."""
    by_over = innings.groupby("over").agg(runs=("runs", "sum"), wickets=("outs", "sum"))
    by_over["score"] = by_over["runs"].cumsum()
    return [dict(over=int(over) + 1, runs=int(row.runs), wickets=int(row.wickets), score=int(row.score))
            for over, row in by_over.iterrows()]


def _innings(number: int, innings: pd.DataFrame, names: dict[str, str], lineup: list[str]) -> dict:
    batting = _batting(innings, names)
    batted = {line["player_id"] for line in batting}
    return dict(
        number=int(number), team=innings["bat_team"].iloc[0], runs=int(innings["runs"].sum()),
        wickets=int(innings["outs"].sum()), overs=overs_text(innings["legal"].sum()),
        target=None if pd.isna(innings["target"].iloc[0]) else int(innings["target"].iloc[0]),
        batting=batting,
        did_not_bat=[names.get(player, "Unknown") for player in lineup if player not in batted],
        bowling=_bowling(innings, names), extras=_extras(innings),
        fall_of_wickets=_fall_of_wickets(innings, names), partnerships=_partnerships(innings, names),
        by_over=_overs(innings),
    )


@per_database(max_entries=300)
def scorecard(match_id: str) -> dict:
    """Every innings of a cricket match, as cards and as the numbers behind the graphics."""
    balls, names = _load(match_id)
    lineups: dict[str, list[str]] = {}
    for row in q("select team, player_id from ck_lineups where match_id = ?", [match_id]):
        lineups.setdefault(row["team"], []).append(row["player_id"])
    return dict(innings=[
        _innings(number, innings, names, lineups.get(innings["bat_team"].iloc[0], []))
        for number, innings in balls.groupby("innings")
    ])
