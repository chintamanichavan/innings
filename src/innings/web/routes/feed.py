"""The front page, the records, and a reader's own teams."""
from __future__ import annotations

import hashlib
from datetime import date

from fastapi import APIRouter, Depends, HTTPException

from ...config import FULL_MEMBERS
from .. import forecasts, matches
from ..db import q
from ..specs import known_sport

router = APIRouter(prefix="/api", dependencies=[Depends(known_sport)])

# Opportunities over the last ten games before a player can be called hot or cold.
HOT_FLOOR = {"ck": dict(bat=40, bowl=40)}
CLASSIC_POOL = 60        # the classic of the day is one of this many great games
RECENT_DAYS = 10         # the game of the week comes from the last few days of data
MAX_FOLLOWED = 12


def _daily_pick(sport: str, today: date) -> int:
    """A number that changes once a day, to rotate the classic and the play of the day."""
    return int(hashlib.sha256(f"{today}:{sport}".encode()).hexdigest(), 16) % CLASSIC_POOL


def _form(sport: str, league: str, role: str, order: str) -> list[dict]:
    """Players ranked by runs above average over their last ten games."""
    return q(f"""select h.player_id, p.name, h.{role}_v as value, h.{role}_n as n, h.games
                 from hot h join players p using (sport, player_id)
                 where h.sport = ? and h.league = ? and h.{role}_n >= ?
                 order by value {order} limit 6""", [sport, league, HOT_FLOOR[sport][role]])


def _form_leagues(sport: str) -> list[str]:
    rows = q("""select league, max(last_date) as latest from hot where sport = ?
                group by league order by latest desc""", [sport])
    return [row["league"] for row in rows]


@router.get("/home")
def home(sport: str, league: str = ""):
    today = date.today()
    latest = q("select max(date) as d from matches where sport = ?", [sport])[0]["d"]
    major = f"m.sport = ? and {matches.MAJOR}"
    decided = f"{major} and m.winner is not null"
    rotate = _daily_pick(sport, today)

    best = matches.cards(f"{decided} and m.date >= ?::date - interval {RECENT_DAYS} day",
                         [sport, latest], "s.thrill desc", 1)
    classic = matches.cards(decided, [sport], "s.thrill desc, s.excitement desc", 1, offset=rotate)
    on_this_day = matches.cards(
        f"{major} and month(m.date) = ? and day(m.date) = ? and year(m.date) < ?",
        [sport, today.month, today.day, today.year], "s.thrill desc", 4)

    leagues = _form_leagues(sport)
    form_league = league if league in leagues else ("IPL" if "IPL" in leagues else leagues[0])
    record = forecasts.tally(forecasts.calls(sport))
    return dict(
        latest=latest,
        recent=matches.cards(major, [sport], "m.date desc, m.match_id desc", 12),
        lead=matches.summary(sport, best[0]["match_id"]) if best else None,
        classic=classic[0] if classic else None,
        on_this_day=on_this_day,
        top_play=matches.plays(f"t.sport = ? and {matches.MAJOR}", [sport], 1, offset=rotate)[0],
        hot_league=form_league, hot_leagues=leagues,
        hot_bat=_form(sport, form_league, "bat", "desc"),
        cold_bat=_form(sport, form_league, "bat", "asc"),
        hot_bowl=_form(sport, form_league, "bowl", "desc"),
        forecast=dict(n=record["n"], right=record["right"]),
    )


@router.get("/records")
def records(sport: str, kind: str = "thrillers", league: str = ""):
    in_league, params = (" and m.league = ?", [league]) if league else ("", [])
    decided = f"m.sport = ? and m.winner is not null and m.note is distinct from 'Awarded'{in_league}"
    if kind == "thrillers":
        # Thrill ranks a match inside its own league, so a Test does not win on length alone.
        return matches.cards(decided, [sport, *params], "s.thrill desc, s.excitement desc", 50)
    if kind == "comebacks":
        return matches.cards(decided, [sport, *params], "s.winner_low asc", 50)
    if kind == "plays":
        return matches.plays(f"t.sport = ?{in_league}", [sport, *params], 50)
    if kind in ("bat_games", "bowl_games"):
        role = "bat" if kind == "bat_games" else "bowl"
        return q(f"""select pm.player_id, p.name, pm.{role}_w as wpa, pm.{role}_v as rae, pm.{role}_n as n,
                            m.match_id, m.date, m.league, m.team1, m.team2
                     from player_match pm join matches m using (sport, match_id)
                     join players p using (sport, player_id)
                     where pm.sport = ?{in_league} order by pm.{role}_w desc limit 50""", [sport, *params])
    raise HTTPException(404, "unknown record list")


@router.get("/onboarding")
def onboarding():
    """Teams to offer on a first visit: the franchise leagues and the full member nations."""
    rows = q("""
        select sport, pool, team, elo from team_state
        where pool in ('IPL', 'BBL', 'PSL', 'CPL', 'SA20', 'T20I', 'T20I (W)')
          and year(last_date) >= (select max(year(last_date)) from team_state) - 1
        order by case pool when 'IPL' then 0 when 'T20I' then 1 when 'T20I (W)' then 2 else 3 end,
                 pool, team""")
    is_nation = lambda row: row["pool"].startswith("T20I")  # noqa: E731
    return [row for row in rows if not is_nation(row) or row["team"].removesuffix(" (W)") in FULL_MEMBERS]


@router.get("/my")
def my_teams(teams: str = ""):
    """The latest game for each followed team. `teams` looks like 'ck|India;ck|Australia'."""
    followed = [item.split("|", 1) for item in teams.split(";") if "|" in item]
    out = []
    for sport, team in followed[:MAX_FOLLOWED]:
        latest = matches.cards("m.sport = ? and (m.team1 = ? or m.team2 = ?)", [sport, team, team],
                               "m.date desc", 1)
        if latest:
            out.append(dict(team=team, match=latest[0]))
    return out
