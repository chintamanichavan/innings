"""The tables the site reads most: one list of matches, a season line for every player,
what each player did in each match, and who was named in each lineup."""
from __future__ import annotations

import duckdb

# Each side's score as a scorecard writes it: "155/8 (20 ov)", "142 (19.4 ov)" when all out,
# and for a Test every innings: "445/6d & 102/3".
SCORE_LINES = """
    with innings as (
        select e.match_id, e.innings, e.bat_team as team, m.format,
               sum(e.runs) as runs, sum(e.outs) as wickets,
               sum(case when e.wide or e.noball then 0 else 1 end) as balls,
               max(e.innings) over (partition by e.match_id) as last_innings
        from ck_events e join ck_matches m using (match_id)
        group by e.match_id, e.innings, e.bat_team, m.format),
    written as (
        select match_id, team, innings,
               runs || case when wickets >= 10 then ''
                            else '/' || wickets
                                 || case when format = 'Test' and innings < last_innings
                                         then 'd' else '' end
                       end
               || case when format = 'Test' then ''
                       else ' (' || balls // 6 || case when balls % 6 > 0 then '.' || balls % 6 else '' end
                            || ' ov)' end as line
        from innings)
    select match_id, team, string_agg(line, ' & ' order by innings) as line
    from written group by match_id, team
"""

# The result as a scorecard states it.
RESULT = """
    case when m.result = 'draw' then 'Match drawn'
         when m.result = 'no result' then 'No result'
         when m.result = 'tie' and m.winner is not null
             then 'Match tied (' || m.winner || ' won the Super Over)'
         when m.result = 'tie' then 'Match tied'
         when m.method is not null then m.winner || ' won (' || m.method || ')'
         when m.winner = m.team2 and m.format != 'Test' and m.max_balls > m.balls2 then
             m.winner || ' won ' || m.note || ' (' || (m.max_balls - m.balls2) || ' balls left)'
         else m.winner || ' won ' || m.note end
"""


# Which rendered picture a match's card shows (frontend/public/cards, made by animation/card_*.py):
# a final gets the trophy, a run feast the six, a side bowled out the broken stumps.
ART = """
    case when m.stage = 'Final' then 'trophy'
         when (m.format = 'T20' and greatest(m.score1, m.score2) >= 200)
           or (m.format = 'ODI' and greatest(m.score1, m.score2) >= 330) then 'six'
         when (m.winner = m.team1 and m.wkts2 >= 10) or (m.winner = m.team2 and m.wkts1 >= 10) then 'stumps'
         else 'ground' end
"""


def _build_matches(con: duckdb.DuckDBPyConnection) -> None:
    """matches: one shape for every sport. `team1` always batted first.

    `league` is what a fan would call the competition. `pool` groups teams that play each
    other, for ratings. `line1`, `line2` and `result` are the score as a fan reads it.
    """
    con.execute(f"""
        create or replace table matches as
        with lines as ({SCORE_LINES})
        select 'ck' as sport, m.match_id, m.date, m.year,
               m.competition || case when m.gender = 'female' then ' (W)' else '' end as league,
               m.competition || case when m.gender = 'female' then ' (W)' else '' end as pool,
               m.format as fmt, m.venue, m.team1, m.team2, m.winner, m.score1, m.score2, m.note,
               one.line as line1, two.line as line2, {RESULT} as result, {ART} as art
        from ck_matches m
        left join lines one on one.match_id = m.match_id and one.team = m.team1
        left join lines two on two.match_id = m.match_id and two.team = m.team2
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
