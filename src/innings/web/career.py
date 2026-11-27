"""A player's career as every cricket site opens a profile: one line per format.

Batting: matches, innings, not outs, runs, highest score, average, balls, strike rate,
hundreds, fifties, fours and sixes. Bowling: matches, innings, balls, runs, wickets, best
figures, average, economy, strike rate, and four- and five-wicket hauls.
"""
from __future__ import annotations

from .db import per_database, q

LEAGUE = "m.competition || case when m.gender = 'female' then ' (W)' else '' end"
# Internationals first, longest format first, as a profile lists them. Leagues follow, by matches.
FIRST = ["Test", "ODI", "T20I", "Test (W)", "ODI (W)", "T20I (W)"]


def _in_order(rows: list[dict]) -> list[dict]:
    def place(row: dict) -> tuple:
        league = row["league"]
        return (FIRST.index(league) if league in FIRST else len(FIRST), -row["matches"], league)
    return sorted(rows, key=place)


def _matches(player_id: str) -> dict[str, int]:
    rows = q(f"""select {LEAGUE} as league, count(*) as n from ck_lineups l join ck_matches m using (match_id)
                 where l.player_id = ? group by 1""", [player_id])
    return {row["league"]: row["n"] for row in rows}


def _batting(player_id: str, played: dict[str, int]) -> list[dict]:
    rows = q(f"""
        with innings as (
            select e.match_id, e.innings, {LEAGUE} as league,
                   sum(case when e.batter_id = ? then e.runs_bat else 0 end) as runs,
                   sum(case when e.batter_id = ? and not e.wide then 1 else 0 end) as balls,
                   sum(case when e.batter_id = ? and e.runs_bat = 4 then 1 else 0 end) as fours,
                   sum(case when e.batter_id = ? and e.runs_bat = 6 then 1 else 0 end) as sixes,
                   coalesce(bool_or(e.dismissed_id = ?), false) as out
            from ck_events e join ck_matches m using (match_id)
            where e.batter_id = ? or e.non_striker_id = ?
            group by all)
        select league, count(*) as innings, count(*) filter (not out) as not_outs, sum(runs) as runs,
               arg_max(runs || case when out then '' else '*' end, runs * 2 + (not out)::int) as best,
               sum(balls) as balls, count(*) filter (runs >= 100) as hundreds,
               count(*) filter (runs between 50 and 99) as fifties, sum(fours) as fours, sum(sixes) as sixes,
               count(*) filter (out) as outs
        from innings group by league""", [player_id] * 7)
    for row in rows:
        row["matches"] = played.get(row["league"], row["innings"])
        row["average"] = row["runs"] / row["outs"] if row["outs"] else None
        row["strike_rate"] = 100 * row["runs"] / row["balls"] if row["balls"] else None
    return _in_order(rows)


def _bowling(player_id: str, played: dict[str, int]) -> list[dict]:
    rows = q(f"""
        with spells as (
            select e.match_id, e.innings, {LEAGUE} as league,
                   sum(case when e.wide or e.noball then 0 else 1 end) as balls,
                   sum(e.runs - e.byes) as runs, sum(e.bowler_wicket::int) as wickets
            from ck_events e join ck_matches m using (match_id)
            where e.bowler_id = ? group by all)
        select league, count(*) as innings, sum(balls) as balls, sum(runs) as runs, sum(wickets) as wickets,
               arg_max(wickets || '/' || runs, wickets * 1000 - runs) as best,
               count(*) filter (wickets = 4) as fours, count(*) filter (wickets >= 5) as fives
        from spells group by league""", [player_id])
    for row in rows:
        row["matches"] = played.get(row["league"], row["innings"])
        wickets, balls = row["wickets"], row["balls"]
        row["average"] = row["runs"] / wickets if wickets else None
        row["economy"] = 6 * row["runs"] / balls if balls else None
        row["strike_rate"] = balls / wickets if wickets else None
        if not wickets:
            row["best"] = "–"      # no wickets, so no best figures to speak of
    return _in_order(rows)


def _recent(player_id: str, count: int = 10) -> list[dict]:
    """The latest matches: what they made with the bat and took with the ball, and against whom."""
    return q(f"""
        with game as (
            select e.match_id,
                   sum(case when e.batter_id = ? then e.runs_bat else 0 end) as runs,
                   sum(case when e.batter_id = ? and not e.wide then 1 else 0 end) as faced,
                   bool_or(e.batter_id = ? or e.non_striker_id = ?) as batted,
                   coalesce(bool_or(e.dismissed_id = ?), false) as out,
                   sum(case when e.bowler_id = ? then e.bowler_wicket::int else 0 end) as wickets,
                   sum(case when e.bowler_id = ? then e.runs - e.byes else 0 end) as conceded,
                   sum(case when e.bowler_id = ? and not (e.wide or e.noball) then 1 else 0 end) as bowled,
                   any_value(case when e.batter_id = ? or e.bowler_id = ? then
                       case when e.batter_id = ? then e.field_team else e.bat_team end end) as opponent
            from ck_events e
            where e.batter_id = ? or e.non_striker_id = ? or e.bowler_id = ?
            group by e.match_id)
        select g.*, m.date, {LEAGUE} as league from game g join ck_matches m using (match_id)
        order by m.date desc, g.match_id desc limit ?""", [player_id] * 14 + [count])


@per_database(max_entries=200)
def career(player_id: str) -> dict:
    played = _matches(player_id)
    return {"batting": _batting(player_id, played), "bowling": _bowling(player_id, played),
            "recent": _recent(player_id)}
