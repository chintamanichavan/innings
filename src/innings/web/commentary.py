"""Ball-by-ball commentary of a finished match, over by over, as cricket sites print it.

Each ball reads "Siraj to Rashid Khan, FOUR". Each over ends with a summary: runs in the
over, the score, the batters in and the bowler's figures. The scoreboard arithmetic is the
live stream's own (`stream/card.py`), so the two can never disagree.
"""
from __future__ import annotations

from fastapi import HTTPException

from ..stream.card import Card, ball_mark, ball_words
from .db import per_database, q

BALLS = """
    select e.seq, e.innings, e."over", e.bat_team, e.runs, e.runs_bat, e.wide, e.noball, e.byes, e.outs,
           e.bowler_wicket, e.dismissal, e.wp1, e.wp1_post, m.team1,
           b.name as batter, n.name as non_striker, p.name as bowler, d.name as dismissed, f.name as fielder
    from ck_ev e join ck_matches m using (match_id)
    left join ck_players b on b.player_id = e.batter_id
    left join ck_players n on n.player_id = e.non_striker_id
    left join ck_players p on p.player_id = e.bowler_id
    left join ck_players d on d.player_id = e.dismissed_id
    left join ck_players f on f.player_id = e.fielder_id
    where e.match_id = ? order by e.seq"""
BIG_SWING = 0.08   # a ball that moves the win chance this much gets its swing printed


def _ball(row: dict, card: Card) -> dict:
    """One line of commentary, with the swing in the batting side's chance when it is large."""
    batting_first = row["bat_team"] == row["team1"]
    swing = (row["wp1_post"] - row["wp1"]) * (1 if batting_first else -1)
    return {"at": card.label, "text": f"{row['bowler']} to {row['batter']}, {ball_words(row)}",
            "mark": ball_mark(row), "wicket": card.last_wicket if row["outs"] else None,
            "swing": round(swing, 3) if abs(swing) >= BIG_SWING else None}


def _over_end(card: Card, runs: int, score: int, wickets: int) -> dict:
    view = card.view()
    return {"runs": runs, "score": f"{score}/{wickets}",
            "batters": [{"name": b["name"], "runs": b["runs"], "balls": b["balls"]} for b in view["batters"]],
            "bowler": view["bowler"]}


@per_database(max_entries=100)
def commentary(match_id: str) -> dict:
    rows = q(BALLS, [match_id])
    if not rows:
        raise HTTPException(404, "no balls recorded for this match")
    innings: list[dict] = []
    card = Card()
    score = wickets = over_runs = 0
    for row in rows:
        if not innings or row["innings"] != innings[-1]["number"]:
            innings.append({"number": row["innings"], "team": row["bat_team"], "overs": []})
            card, score, wickets = Card(), 0, 0
        overs = innings[-1]["overs"]
        if not overs or overs[-1]["over"] != row["over"] + 1:
            overs.append({"over": row["over"] + 1, "balls": [], "end": None})
            over_runs = 0
        score, wickets, over_runs = score + row["runs"], wickets + row["outs"], over_runs + row["runs"]
        card.take(row, score, wickets)
        overs[-1]["balls"].append(_ball(row, card))
        overs[-1]["end"] = _over_end(card, over_runs, score, wickets)
    return {"innings": innings}
