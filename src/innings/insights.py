"""Tables for fans, built on top of the valued plays: how thrilling each match was, the
biggest plays, team seasons, venues, player splits, clutch, skill profiles and recent form."""
from __future__ import annotations

import duckdb

from .config import CRICKET_FORMATS
from .scopes import in_format

TOP_PLAYS = 300        # biggest single plays kept
FORM_GAMES = 10        # recent form is a player's last ten games
FORM_WINDOW_DAYS = 45  # only players active this recently in their league are listed

# ---- skill profiles ----

# The five skills behind a profile, as (label, SQL over a player's summed seasons).
BATTING_SKILLS = [
    ("Power", "sum(4 * fours + 6 * sixes) / sum(balls)"), ("Contact", "1 - sum(dots) / sum(balls)"),
    ("Patience", "sum(balls) / greatest(sum(outs), 1)"), ("Value", "sum(rae) / sum(balls)"),
    ("Clutch", "sum(clutch) / sum(balls)")]
BOWLING_SKILLS = [
    ("Strike power", "sum(wkts) / sum(balls)"), ("Control", "1 - sum(extras) / sum(balls)"),
    ("Run prevention", "-sum(runs) / sum(balls)"), ("Value", "sum(rae) / sum(balls)"),
    ("Clutch", "sum(clutch) / sum(balls)")]
SKILLS = {"bat": BATTING_SKILLS, "bowl": BOWLING_SKILLS}
DIMS = {role: [label for label, _ in skills] for role, skills in SKILLS.items()}

SEASON_TABLE = {"bat": ("ck_bat", "balls"), "bowl": ("ck_bowl", "balls")}


def profile_pools() -> list[dict]:
    """Every group of players ranked against each other: one per role and format."""
    pools = []
    for role, (table, chances) in SEASON_TABLE.items():
        for fmt in CRICKET_FORMATS.values():
            pools.append(dict(sport="ck", role=role, fmt=fmt.name, table=table, chances=chances,
                              floor=fmt.profile_floor, where=in_format(fmt.name)))
    return pools


def _build_profiles(con: duckdb.DuckDBPyConnection) -> None:
    """profiles: each qualified player's percentile, 0 to 100, on the five skills of their role."""
    con.execute("drop table if exists profiles")
    for index, pool in enumerate(profile_pools()):
        skills = SKILLS[pool["role"]]
        raw = ", ".join(f"{sql} as r{n}" for n, (_, sql) in enumerate(skills, start=1))
        ranked = ", ".join(f"100 * percent_rank() over (order by r{n}) as d{n}" for n in range(1, 6))
        target = "create table profiles as" if index == 0 else "insert into profiles"
        con.execute(f"""
            {target}
            with career as (
                select player_id, sum({pool["chances"]}) as n, {raw}
                from {pool["table"]} where {pool["where"]}
                group by player_id having sum({pool["chances"]}) >= {pool["floor"]}
            )
            select '{pool["sport"]}' as sport, '{pool["role"]}' as role, '{pool["fmt"]}' as fmt,
                   career.player_id, p.name, career.n, {ranked}, r1, r2, r3, r4, r5
            from career join players p on p.sport = '{pool["sport"]}' and p.player_id = career.player_id
        """)


# ---- matches ----

def _build_match_stats(con: duckdb.DuckDBPyConnection) -> None:
    """match_stats: how far the win chance travelled in each match, and what that says about it."""
    con.execute("""
        create or replace table match_stats as
        with plays as (
            select 'ck' as sport, match_id, wp1, wp1_post from ck_ev
        ), swings as (
            select sport, match_id,
                   sum(abs(wp1_post - wp1)) as excitement,
                   min(least(wp1, wp1_post)) as low1,
                   max(greatest(wp1, wp1_post)) as high1,
                   max(abs(wp1_post - wp1)) as top_swing,
                   count(*) filter (where (wp1 - 0.5) * (wp1_post - 0.5) < 0) as lead_changes
            from plays group by all
        )
        select s.sport, s.match_id, s.excitement, s.top_swing, s.lead_changes,
               -- The winner's worst moment. Lower means a bigger comeback.
               case when m.winner = m.team1 then s.low1
                    when m.winner = m.team2 then 1 - s.high1 end as winner_low,
               -- Thrill ranks a match inside its own league: a five-day Test has far more
               -- swings than a T20, so they are never compared with each other.
               percent_rank() over (partition by s.sport, m.league order by s.excitement) as thrill
        from swings s join matches m using (sport, match_id)
    """)


def _build_top_plays(con: duckdb.DuckDBPyConnection) -> None:
    """top_plays: the plays that moved the win chance most."""
    con.execute(f"""
        create or replace table top_plays as
        select * from (
            select 'ck' as sport, e.match_id, e.seq, e.wp1, e.wp1_post, e.bat_team,
                   e."over" || '.' || e.ball as moment, e.batter_id, e.bowler_id,
                   case when e.outs > 0 then 'OUT ' || e.dismissal else e.runs::varchar end as what
            from ck_ev e
        ) qualify row_number() over (
            partition by sport
            -- Many plays swing by exactly the same amount. The last two keys settle ties the
            -- same way on every build.
            order by abs(wp1_post - wp1) desc, match_id, seq) <= {TOP_PLAYS}
    """)


def _build_team_seasons(con: duckdb.DuckDBPyConnection) -> None:
    """team_season: games, wins, losses and runs for and against, per team, league and year."""
    con.execute("""
        create or replace table team_season as
        select sport, league, pool, year, team, count(*) as g,
               count(*) filter (where winner = team) as w,
               count(*) filter (where winner is not null and winner <> team) as l,
               sum(rf) as rf, sum(ra) as ra
        from (
            select sport, league, pool, year, team1 as team, winner, score1 as rf, score2 as ra
            from matches
            union all
            select sport, league, pool, year, team2, winner, score2, score1 from matches
        ) group by all
    """)


def _build_venues(con: duckdb.DuckDBPyConnection) -> None:
    """venues: scoring and how often the side batting first wins, per ground."""
    con.execute("""
        create or replace table venues as
        select m.sport, m.venue, count(*) as n, min(m.date) as first, max(m.date) as last,
               avg(m.score1) as avg1, avg(m.score2) as avg2,
               avg(case when m.winner = m.team1 then 1.0 when m.winner = m.team2 then 0.0 end) as first_win,
               avg(s.excitement) as excitement,
               mode(m.league order by m.league) as league   -- ordered, so ties break the same way
        from matches m join match_stats s using (sport, match_id)
        where m.venue is not null group by all
    """)


# ---- splits ----

SPLIT_NUMBERS = ("n", "runs", "outs", "rae", "wpa")


def _phase_of_innings() -> str:
    """SQL naming the phase of a ball from its over, using each format's own phase boundaries."""
    def one_format(fmt) -> str:
        branches = [f"""when "over" < {end} then '{label}'""" for _, label, end in fmt.phases[:-1]]
        return f"case {' '.join(branches)} else '{fmt.phases[-1][1]}' end"

    *limited, last = CRICKET_FORMATS.values()
    branches = [f"when fmt = '{fmt.name}' then {one_format(fmt)}" for fmt in limited]
    return f"case {' '.join(branches)} else {one_format(last)} end"


WHICH_INNINGS = ("case when fmt = 'Test' then 'Match innings ' || innings "
                 "when innings = 1 then 'Batting first' else 'Chasing' end")


def _build_splits(con: duckdb.DuckDBPyConnection) -> None:
    """splits: each player's numbers cut one way at a time, per year."""
    numbers = ", ".join(f"{name} double" for name in SPLIT_NUMBERS)
    con.execute(f"""create or replace table splits (
        sport varchar, role varchar, player_id varchar, year int, dim varchar, key varchar, {numbers})""")

    for name, key in (("Phase", _phase_of_innings()), ("Innings", WHICH_INNINGS)):
        con.execute(f"""
            insert into splits
            select 'ck', 'bat', batter_id, m.year, fmt || ' · {name}', {key},
                   count(*), sum(runs_bat), count(*) filter (where dismissed_id = batter_id),
                   sum(bat_rae), sum(wpa)
            from ck_ev e join ck_matches m using (match_id) where not wide group by all
        """)
        con.execute(f"""
            insert into splits
            select 'ck', 'bowl', bowler_id, m.year, fmt || ' · {name}', {key},
                   count(*) filter (where not wide and not noball),
                   sum(runs - byes), sum(bowler_wicket::int), sum(bowl_rae), -sum(wpa)
            from ck_ev e join ck_matches m using (match_id) group by all
        """)


# ---- clutch and form ----

def _add_clutch(con: duckdb.DuckDBPyConnection) -> None:
    """Add `clutch` to the season tables: wins added beyond what the same runs usually buy.

    One run is worth, on average, `wins_per_run` wins. Clutch is what is left of a player's
    win probability added after taking that out. The season tables are rebuilt just before
    this runs, so the column is always new.
    """
    con.execute("create table if not exists constants (sport varchar, name varchar, value double)")
    wins_per_run = con.execute("select sum(wpa * rae) / sum(rae * rae) from ck_ev").fetchone()[0]
    for table in ("ck_bat", "ck_bowl"):
        con.execute(f"""create or replace table {table} as
                        select *, wpa - {wins_per_run} * rae as clutch from {table}""")
    con.execute("delete from constants where sport = 'ck' and name = 'wins_per_run'")
    con.execute("insert into constants values ('ck', 'wins_per_run', ?)", [wins_per_run])


def _build_form(con: duckdb.DuckDBPyConnection) -> None:
    """hot: each recently active player's totals over their last ten games in a league."""
    con.execute(f"""
        create or replace table hot as
        with games as (
            select pm.*, m.date, m.league,
                   row_number() over (partition by pm.sport, m.league, pm.player_id
                                      order by m.date desc, m.match_id desc) as recency,
                   max(m.date) over (partition by pm.sport, m.league) as league_latest
            from player_match pm join matches m using (sport, match_id)
        )
        select sport, player_id, league, max(date) as last_date, count(*) as games,
               sum(bat_n) as bat_n, sum(bat_v) as bat_v, sum(bowl_n) as bowl_n, sum(bowl_v) as bowl_v
        from games where recency <= {FORM_GAMES}
        group by sport, league, player_id, league_latest
        having max(date) >= league_latest - interval {FORM_WINDOW_DAYS} day
    """)


def build(con: duckdb.DuckDBPyConnection) -> None:
    _build_match_stats(con)
    _build_top_plays(con)
    _build_team_seasons(con)
    _build_venues(con)
    _build_splits(con)
    _add_clutch(con)      # profiles rank clutch, so it comes first
    _build_profiles(con)
    _build_form(con)
