"""Leaderboards, players, matches and search."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import career, commentary, matches, players, scorecard
from ..db import q
from ..specs import career_line, known_sport, season_lines, spec_for

router = APIRouter(prefix="/api", dependencies=[Depends(known_sport)])

MAX_LEADERS = 500
MAX_MATCHES = 1000


@router.get("/meta")
def meta():
    """What the database holds: leagues, their years, and the model scores."""
    return dict(
        leagues=q("""select sport, league, min(year) as first, max(year) as last,
                            count(*) as matches, max(date) as latest
                     from matches group by sport, league
                     order by (league = 'IPL') desc, count(*) desc"""),
        metrics=q("select * from model_metrics"),
        events=q("select 'ck' as sport, count(*) as n from ck_ev"),
    )


@router.get("/leaders")
def leaders(sport: str, role: str = "bat", league: str = "", year: int | None = None,
            min_opps: int | None = None, sort: str | None = None, asc: bool = False, limit: int = 100):
    spec = spec_for(sport, role)
    sort = sort if sort in spec.sortable() else "rae"
    # An all-years board asks for three seasons' worth of chances by default.
    floor = min_opps if min_opps is not None else spec.floor * (1 if year else 3)
    where, params = "league = ?", [league]
    if year:
        where += " and year = ?"
        params.append(year)
    rows = q(f"""
        select t.player_id, p.name, arg_max(t.team, t.year) as team, {spec.select()}
        from {spec.table} t join players p on p.sport = ? and p.player_id = t.player_id
        where {where}
        group by t.player_id, p.name having sum({spec.opps}) >= ?
        order by {sort} {"asc" if asc else "desc"} nulls last limit ?""",
             [sport, *params, floor, min(limit, MAX_LEADERS)])
    return dict(columns=spec.columns(), rows=rows, sort=sort, min_opps=floor, opps=spec.opps)


@router.get("/search")
def search(sport: str, term: str = Query("", alias="q")):
    return q("""select player_id, name, n from players
                where sport = ? and name ilike ? and n > 0 order by n desc limit 12""",
             [sport, f"%{term}%"])


@router.get("/find")
def find(term: str = ""):
    """Players and teams whose name contains `term`."""
    like = f"%{term}%"
    return dict(
        players=q("""select sport, player_id, name, n from players where name ilike ? and n > 0
                     order by n desc limit 8""", [like]),
        teams=q("""select sport, pool, team from team_state where team ilike ?
                   order by games desc limit 5""", [like]),
    )


@router.get("/player/{sport}/{player_id}")
def player(sport: str, player_id: str):
    name = players.name_of(sport, player_id)
    if name is None:
        raise HTTPException(404, "no such player")
    roles = {}
    for role in ("bat", "bowl"):
        spec = spec_for(sport, role)
        seasons = season_lines(spec, player_id)
        if seasons:
            roles[role] = dict(columns=spec.columns(), rows=seasons, total=career_line(spec, player_id))
    return dict(name=name, roles=roles)


@router.get("/player-extra/{sport}/{player_id}")
def player_extra(sport: str, player_id: str):
    if players.name_of(sport, player_id) is None:
        raise HTTPException(404, "no such player")
    return players.extra(sport, player_id)


@router.get("/career/{player_id}")
def career_of(player_id: str):
    """A career summary by format, as a profile opens, and the latest matches."""
    if players.name_of("ck", player_id) is None:
        raise HTTPException(404, "no such player")
    return career.career(player_id)


@router.get("/matches")
def match_list(sport: str, league: str = "", year: int | None = None, team: str = "", limit: int = 200):
    where, params = "sport = ?", [sport]
    if league:
        where += " and league = ?"
        params.append(league)
    if year:
        where += " and year = ?"
        params.append(year)
    if team:
        where += " and (team1 = ? or team2 = ?)"
        params += [team, team]
    return q(f"""select match_id, date, league, venue, team1, team2, score1, score2, winner, note,
                        line1, line2, result
                 from matches where {where}
                 order by date desc, match_id desc limit ?""", [*params, min(limit, MAX_MATCHES)])


@router.get("/teams")
def team_names(sport: str, league: str):
    rows = q("""select distinct team from (
                    select team1 as team from matches where sport = ? and league = ?
                    union all select team2 from matches where sport = ? and league = ?)
                order by team""", [sport, league, sport, league])
    return [row["team"] for row in rows]


@router.get("/scorecard/{match_id}")
def scorecard_of(match_id: str):
    """A cricket match's batting and bowling cards, and the numbers behind its graphics."""
    return scorecard.scorecard(match_id)


@router.get("/commentary/{match_id}")
def commentary_of(match_id: str):
    """Every ball, over by over, with a summary at the end of each over."""
    return commentary.commentary(match_id)


@router.get("/match/{sport}/{match_id}")
def match(sport: str, match_id: str):
    return matches.payload(sport, match_id)


MATCHUP = (("balls", "Balls", 0), ("runs", "Runs", 0), ("outs", "Out", 0), ("sr", "SR", 1),
           ("rae", "RAE", 1), ("wpa", "WPA", 2))


@router.get("/matchup")
def matchup(sport: str, batter: str, bowler: str):
    """One batter against one bowler: a total row, then one row per year."""
    rows = q("""
        select m.year, count(*) filter (where not wide) as balls, sum(runs_bat) as runs,
               sum(bowler_wicket::int) as outs,
               100.0 * sum(runs_bat) / nullif(count(*) filter (where not wide), 0) as sr,
               sum(e.bat_rae) as rae, sum(e.wpa) as wpa
        from ck_ev e join ck_matches m using (match_id)
        where e.batter_id = ? and e.bowler_id = ?
        group by rollup (m.year) order by m.year desc nulls first""", [batter, bowler])
    columns = [dict(key=key, label=label, digits=digits) for key, label, digits in MATCHUP]
    return dict(columns=columns, rows=rows)
