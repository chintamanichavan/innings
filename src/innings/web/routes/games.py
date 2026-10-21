"""The puzzle corner: Who am I, higher or lower, and you against the model."""
from __future__ import annotations

import hashlib
import random
from datetime import date

from fastapi import APIRouter, Depends

from ...config import FULL_MEMBERS, INTERNATIONAL
from .. import matches, players
from ..db import q
from ..specs import career_line, known_sport, season_lines, spec_for

router = APIRouter(prefix="/api/game", dependencies=[Depends(known_sport)])

FAMOUS = 250   # the daily player is drawn from this many of the busiest careers
_members = ", ".join(f"'{t}'" for t in sorted(FULL_MEMBERS))
_international = " or ".join(f"t.league like '{name}%'" for name in INTERNATIONAL)
# A season a fan would recognise: a franchise league, or a full member nation.
KNOWN_SEASON = f"(not ({_international}) or replace(t.team, ' (W)', '') in ({_members}))"

# (column, what to call it, table, opportunities column, opportunities needed, extra filter)
HIGHER_LOWER = {
    "ck": [("runs", "runs", "ck_bat", "balls", 250, "true"),
           ("sixes", "sixes", "ck_bat", "balls", 250, "true"),
           ("wkts", "wickets", "ck_bowl", "balls", 200, "league not like 'T20I%'")],
}


def _todays_player(sport: str, day: str) -> dict:
    """The same player for everyone on a given day."""
    famous = q("select player_id, name from players where sport = ? order by n desc limit ?", [sport, FAMOUS])
    return famous[int(hashlib.sha256(f"{day}:{sport}:who".encode()).hexdigest(), 16) % len(famous)]


def _hints(sport: str, player_id: str, name: str) -> list[dict]:
    """Six clues, from vague to nearly giving it away."""
    role = players.main_role(sport, player_id)
    spec = spec_for(sport, role)
    seasons = season_lines(spec, player_id)
    best = max(seasons, key=lambda season: season["rae"] or 0)
    years = sorted({season["year"] for season in seasons})
    profile = players.primary(players.profiles(sport, player_id)).get(role, {})
    job = "Batter" if role == "bat" else "Bowler"
    return [
        dict(title="The basics", text=f"{job}. In our data from {years[0]} to {years[-1]}."),
        dict(title="Skill profile", profile=profile.get("dims", [])),
        dict(title="Career line", columns=spec.columns(), row=career_line(spec, player_id)),
        dict(title=f"Best season: {best['year']}, {best['league']}", columns=spec.columns(), row=best),
        dict(title="Teams", text=", ".join(sorted({season["team"] for season in seasons}))),
        dict(title="Initials", text=" ".join(word[0] + "." for word in name.split())),
    ]


@router.get("/daily")
def daily(sport: str, shown: int = 1, day: str = ""):
    """The first `shown` clues for the day's player. The answer stays on the server."""
    day = day or str(date.today())
    answer = _todays_player(sport, day)
    hints = _hints(sport, answer["player_id"], answer["name"])
    return dict(day=day, total=len(hints), hints=hints[:max(1, min(shown, len(hints)))])


@router.get("/guess")
def guess(sport: str, player_id: str, day: str, last: bool = False):
    """Check a guess. The answer is given only when it is right or the guesses have run out."""
    answer = _todays_player(sport, day)
    correct = answer["player_id"] == player_id
    return dict(correct=correct, answer=answer if correct or last else None)


@router.get("/higher-lower")
def higher_lower(sport: str):
    """Fourteen recognisable player seasons for one randomly chosen stat."""
    column, label, table, opps, floor, extra = random.choice(HIGHER_LOWER[sport])
    cards = q(f"""select t.player_id, p.name, t.year, t.league, t.team, t.{column} as value
                  from {table} t join players p on p.sport = ? and p.player_id = t.player_id
                  where t.{opps} >= ? and {extra} and {KNOWN_SEASON}
                  order by random() limit 14""", [sport, floor])
    return dict(metric=label, digits=0, cards=cards)


@router.get("/pick")
def pick(sport: str):
    """Ten past matches with the model's call, made from data before each one."""
    return q(f"""select m.match_id, m.date, m.league, m.venue, m.team1, m.team2,
                        m.score1, m.score2, m.winner, p.p_full as p_model
                 from predictions p join matches m using (sport, match_id)
                 where p.sport = ? and {matches.MAJOR} order by random() limit 10""", [sport])
