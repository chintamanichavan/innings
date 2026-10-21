"""Questions asked of the lake: things only a hundred thousand seasons can tell you.

Each one is a single SQL query over every ball, run by DuckDB straight off the Parquet
files. The seconds each took are kept, because being quick over this much data is the point.
"""
from __future__ import annotations

import time

import duckdb

from .lake import LAKE

BALLS = f"read_parquet('{LAKE}/balls/*.parquet')"
PEOPLE = f"read_parquet('{LAKE}/people.parquet')"
OUTCOMES = f"read_parquet('{LAKE}/outcomes.parquet')"
REAL_MOST_RUNS = 973        # Virat Kohli, 2016
REAL_MOST_WICKETS = 32      # Harshal Patel 2021 and Dwayne Bravo 2013
REAL_HIGHEST_TOTAL = 287    # Sunrisers Hyderabad, 2024
REAL_HIGHEST_SCORE = 175    # Chris Gayle, 2013


def _ask(con: duckdb.DuckDBPyConnection, sql: str) -> tuple[list[tuple], float]:
    started = time.time()
    rows = con.execute(sql).fetchall()
    return rows, round(time.time() - started, 2)


def run() -> list[dict]:
    con = duckdb.connect()
    found = []

    def add(title: str, sql: str, say) -> None:
        rows, seconds = _ask(con, sql)
        found.append({"title": title, "seconds": seconds, **say(rows)})

    seasons = con.execute(f"select count(distinct season) from read_parquet('{LAKE}/matches/*.parquet')"
                          ).fetchone()[0]

    add("The highest team total", f"""
        with totals as (
            select sum(o.runs) as total from {BALLS} b join {OUTCOMES} o using (outcome)
            group by b.season, b.match, b.innings)
        select max(total), avg(total), count(*) filter (total > {REAL_HIGHEST_TOTAL}), count(*)
        from totals""",
        lambda rows: {
            "value": f"{rows[0][0]}",
            "text": f"The biggest of {rows[0][3]:,} innings. The real record is {REAL_HIGHEST_TOTAL}, and "
                    f"{rows[0][2]:,} simulated innings beat it. The average innings made {rows[0][1]:.0f}."})

    add("Most runs by one batter in a season", f"""
        with runs as (
            select b.season, b.batter, sum(o.bat_runs) as runs
            from {BALLS} b join {OUTCOMES} o using (outcome) group by b.season, b.batter),
        best as (select season, max(runs) as top, arg_max(batter, runs) as batter from runs group by season)
        select (select max(top) from best),
               (select count(*) from best where top >= {REAL_MOST_RUNS}),
               (select p.name from best join {PEOPLE} p on p.person = best.batter
                group by p.name order by count(*) desc limit 1),
               (select max(n) from (select count(*) as n from best group by batter))""",
        lambda rows: {
            "value": f"{rows[0][0]}",
            "text": f"The real record is {REAL_MOST_RUNS}. A batter reached it in {rows[0][1]:,} of "
                    f"{seasons:,} seasons. {rows[0][2]} was the top scorer most often: "
                    f"{rows[0][3] / seasons:.0%} of seasons."})

    add("Most wickets by one bowler in a season", f"""
        with wickets as (
            select b.season, b.bowler, count(*) as wickets
            from {BALLS} b join {OUTCOMES} o using (outcome) where o.wicket group by b.season, b.bowler),
        best as (select season, max(wickets) as top, arg_max(bowler, wickets) as bowler
                 from wickets group by season)
        select (select max(top) from best),
               (select count(*) from best where top > {REAL_MOST_WICKETS}),
               (select p.name from best join {PEOPLE} p on p.person = best.bowler
                group by p.name order by count(*) desc limit 1),
               (select max(n) from (select count(*) as n from best group by bowler))""",
        lambda rows: {
            "value": f"{rows[0][0]}",
            "text": f"The real record is {REAL_MOST_WICKETS}. It was beaten in {rows[0][1]:,} seasons. "
                    f"{rows[0][2]} took the most wickets most often: {rows[0][3] / seasons:.0%} of seasons. "
                    f"Every wicket here goes to the bowler, run-outs included."})

    add("The highest score by one batter", f"""
        with scores as (
            select b.batter, sum(o.bat_runs) as runs
            from {BALLS} b join {OUTCOMES} o using (outcome)
            group by b.season, b.match, b.innings, b.batter)
        select max(s.runs), arg_max(p.name, s.runs), count(*) filter (s.runs >= 100),
               count(*) filter (s.runs > {REAL_HIGHEST_SCORE})
        from scores s join {PEOPLE} p on p.person = s.batter""",
        lambda rows: {
            "value": f"{rows[0][0]}",
            "text": f"By {rows[0][1]}. "
                    f"The real record is {REAL_HIGHEST_SCORE}, beaten {rows[0][3]:,} times here. "
                    f"There were {rows[0][2] / seasons:.1f} hundreds a season."})

    add("Sixes in a season", f"""
        with sixes as (select season, count(*) as n from {BALLS} where outcome = 5 group by season)
        select avg(n), min(n), max(n) from sixes""",
        lambda rows: {
            "value": f"{rows[0][0]:,.0f}",
            "text": f"On average. The quietest season had {rows[0][1]:,} and the wildest {rows[0][2]:,}."})
    return found
