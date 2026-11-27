"""The ball-tagging tool: matches to tag, a match's balls with this tagger's tags, and saving."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, HTTPException

from ... import tagging
from ...balls import phase_key
from ..db import q

router = APIRouter(prefix="/api/tag")

BALLS_SQL = f"""
select e.innings, e."over", e.ball, e.bat_team, e.field_team, b.name as batter, w.name as bowler,
       e.bowler_id, e.runs, e.runs_bat, e.extras, e.wide, e.noball, e.dismissal,
       e.dismissal is not null as wicket, {phase_key()} as phase
from ck_ev e join ck_players b on b.player_id = e.batter_id
             join ck_players w on w.player_id = e.bowler_id
where e.match_id = ? order by e.seq
"""


@router.get("/fields")
def fields():
    """Each field's values in key order, and whether they are in order."""
    return [dict(name=name, values=values, ordered=ordered)
            for name, (values, ordered) in tagging.FIELDS.items()]


@router.get("/matches")
def matches(tagger: str = "", league: str = "SMAT", year: int = 2026):
    """A league's matches for one season, newest first, with how many balls this tagger
    has tagged in each."""
    rows = q("""select m.match_id, m.date, m.team1, m.team2, m.venue, m.result,
                       count(*) as balls, count(*) filter (where b.phase = 'death') as death
                from ck_balls b join ck_matches m using (match_id)
                where b.league = ? and b.year = ? group by all order by m.date desc, m.match_id""",
             [league, year])
    tagged: dict[str, int] = {}
    for (who, match_id, *_) in tagging.latest():
        if who == tagger:
            tagged[match_id] = tagged.get(match_id, 0) + 1
    return [row | {"tagged": tagged.get(row["match_id"], 0)} for row in rows]


@router.get("/match/{match_id}")
def match(match_id: str, tagger: str = ""):
    """Every ball of the match in order, with this tagger's tags and none of anyone
    else's: double-tagging is blind."""
    found = q("select match_id, date, team1, team2, venue, result from ck_matches where match_id = ?",
              [match_id])
    if not found:
        raise HTTPException(404, "no such match")
    mine = {tuple(ball): tag for (who, *ball), tag in tagging.latest().items() if who == tagger}
    balls = [row | {"tag": mine.get((match_id, row["innings"], row["over"], row["ball"]))}
             for row in q(BALLS_SQL, [match_id])]
    return found[0] | {"balls": balls}


@router.post("")
def save(tag: Annotated[dict, Body()]):
    """Add one tag. The ball must exist, and the score sent must be the scorecard's."""
    ball = q("""select runs, wide, noball, dismissal is not null as wicket from ck_ev
                where match_id = ? and innings = ? and "over" = ? and ball = ?""",
             [tag.get("match_id"), tag.get("innings"), tag.get("over"), tag.get("ball")])
    if not ball:
        raise HTTPException(400, "no such ball")
    try:
        return tagging.append(tag | {"scored": ball[0]})
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
