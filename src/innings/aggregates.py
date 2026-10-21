"""The tables the site reads most: one list of matches, a season line for every player,
what each player did in each match, and who was named in each lineup."""
from __future__ import annotations

import duckdb


def _build_matches(con: duckdb.DuckDBPyConnection) -> None:
    """matches: one shape for every sport. `team1` always batted first.

    `league` is what a fan would call the competition. `pool` groups teams that play each
    other, for ratings.
    """
    con.execute("""
        create or replace table matches as
        select 'ck' as sport, match_id, date, year,
               competition || case when gender = 'female' then ' (W)' else '' end as league,
               competition || case when gender = 'female' then ' (W)' else '' end as pool,
               format as fmt, venue, team1, team2, winner, score1, score2, note
        from ck_matches
    """)


def _build_cricket_seasons(con: duckdb.DuckDBPyConnection) -> None:
    """ck_bat and ck_bowl: one row per player, year and league."""
    # A dismissal is counted for whoever got out, who is not always the batter on strike.
    con.execute("""
        create or replace table ck_bat as
        with faced as (
            select e.batter_id as player_id, m.year, m.league, arg_max(e.bat_team, m.date) as team,
                   count(distinct e.match_id) as inns, sum(runs_bat) as runs, count(*) as balls,
                   count(*) filter (where runs_bat = 4) as fours,
                   count(*) filter (where runs_bat = 6) as sixes,
                   count(*) filter (where runs_bat = 0) as dots,
                   sum(bat_rae) as rae, sum(wpa) as wpa
            from ck_ev e join matches m on m.sport = 'ck' and m.match_id = e.match_id
            where not e.wide group by all
        ), dismissed as (
            select e.dismissed_id as player_id, m.year, m.league, count(*) as outs
            from ck_ev e join matches m on m.sport = 'ck' and m.match_id = e.match_id
            where e.dismissed_id is not null group by all
        )
        select faced.*, coalesce(dismissed.outs, 0) as outs
        from faced left join dismissed using (player_id, year, league)
    """)
    # Byes are not charged to the bowler. Run-outs are not the bowler's wickets.
    con.execute("""
        create or replace table ck_bowl as
        select e.bowler_id as player_id, m.year, m.league, arg_max(e.field_team, m.date) as team,
               count(distinct e.match_id) as inns,
               count(*) filter (where not wide and not noball) as balls,
               sum(runs - byes) as runs, sum(bowler_wicket::int) as wkts,
               count(*) filter (where runs = 0) as dots,
               count(*) filter (where wide or noball) as extras,
               sum(bowl_rae) as rae, -sum(wpa) as wpa
        from ck_ev e join matches m on m.sport = 'ck' and m.match_id = e.match_id
        group by all
    """)


def _build_player_matches(con: duckdb.DuckDBPyConnection) -> None:
    """player_match: each player's chances (_n), runs above average (_v) and win chance added
    (_w) in each match, batting and bowling. This feeds the ratings used to forecast."""
    con.execute("""
        create or replace table player_match as
        with lines as (
            select 'ck' as sport, match_id, batter_id as player_id, count(*) as bat_n,
                   sum(bat_rae) as bat_v, sum(wpa) as bat_w, 0 as bowl_n, 0.0 as bowl_v, 0.0 as bowl_w
            from ck_ev where not wide group by all
            union all
            select 'ck', match_id, bowler_id, 0, 0.0, 0.0, count(*), sum(bowl_rae), -sum(wpa)
            from ck_ev group by all
        )
        select sport, match_id, player_id,
               sum(bat_n) as bat_n, sum(bat_v) as bat_v, sum(bat_w) as bat_w,
               sum(bowl_n) as bowl_n, sum(bowl_v) as bowl_v, sum(bowl_w) as bowl_w
        from lines group by all
    """)


def _build_players(con: duckdb.DuckDBPyConnection) -> None:
    """players: everyone, with `n`, their total chances, to rank search results."""
    con.execute("""
        create or replace table players as
        select everyone.*, coalesce(chances.n, 0) as n
        from (select 'ck' as sport, player_id, name from ck_players) everyone
        left join (
            select sport, player_id, sum(bat_n + bowl_n) as n from player_match group by all
        ) chances using (sport, player_id)
    """)


def _build_lineups(con: duckdb.DuckDBPyConnection) -> None:
    """lineups: who was named to play, known before the first ball. Cricket publishes its eleven."""
    con.execute("""
        create or replace table lineups as
        select 'ck' as sport, match_id, team, player_id from ck_lineups
    """)


def build(con: duckdb.DuckDBPyConnection) -> None:
    _build_matches(con)
    _build_cricket_seasons(con)
    _build_player_matches(con)
    _build_players(con)      # needs player_match for the totals
    _build_lineups(con)
