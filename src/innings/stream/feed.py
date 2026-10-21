"""Past matches turned back into a feed: the messages a ground would send, in order.

A match is one `start`, an `innings` as each side comes in to bat, one `ball` for every
delivery, and one `end`. A ball carries what happened and nothing the models worked out, so
the scorer has to earn its numbers.
"""
from __future__ import annotations

from collections.abc import Iterator

import duckdb

from ..config import CK_BALLS, FULL_MEMBERS

LIMITED = [fmt for fmt, balls in CK_BALLS.items() if balls]
# Limited-overs matches where both sides batted and one of them won.
PLAYABLE = f"""m.result = 'win' and m.score2 is not null
               and m.format in ({", ".join(f"'{fmt}'" for fmt in LIMITED)})"""


def playable_ids(con: duckdb.DuckDBPyConnection, limit: int | None = None) -> list[str]:
    rows = con.execute(f"""select m.match_id from ck_matches m where {PLAYABLE}
                           order by m.date, m.match_id {f'limit {int(limit)}' if limit else ''}""")
    return [match_id for (match_id,) in rows.fetchall()]


def thrillers(con: duckdb.DuckDBPyConnection, limit: int) -> list[str]:
    """The closest T20 matches between sides a fan knows: the IPL, and the leading nations."""
    known = sorted(FULL_MEMBERS)
    rows = con.execute(f"""
        select m.match_id from ck_matches m join match_stats s on s.sport = 'ck' and s.match_id = m.match_id
        where {PLAYABLE} and m.format = 'T20' and m.gender = 'male' and m.method is null
          and (m.competition = 'IPL' or (m.competition = 'T20I' and m.team1 in ? and m.team2 in ?))
        order by s.thrill desc, m.match_id limit ?""", [known, known, limit])
    return [match_id for (match_id,) in rows.fetchall()]


def _rows(con: duckdb.DuckDBPyConnection, sql: str, params: list) -> Iterator[dict]:
    cursor = con.cursor()
    cursor.execute(sql, params)
    names = [column[0] for column in cursor.description]
    while batch := cursor.fetchmany(20_000):
        for row in batch:
            yield dict(zip(names, row, strict=True))


def starts(con: duckdb.DuckDBPyConnection, match_ids: list[str]) -> dict[str, dict]:
    """The `start` message of each match, with the winner tucked in for its `end`."""
    rows = _rows(con, """
        select m.match_id, m.format as fmt, m.competition, m.year, (m.gender = 'female')::int as female,
               m.team1, m.team2, m.venue, m.date::varchar as date, m.winner
        from ck_matches m where m.match_id in (select unnest(?))""", [match_ids])
    return {row["match_id"]: {"kind": "start", **row} for row in rows}


def balls(con: duckdb.DuckDBPyConnection, match_ids: list[str]) -> Iterator[dict]:
    """Every ball of these matches, match by match, in the order it was bowled."""
    return _rows(con, """
        select 'ball' as kind, e.match_id, e.seq, e.innings, e."over", e.ball, e.runs, e.runs_bat,
               e.wide, e.noball, e.byes, e.outs, e.bowler_wicket, e.dismissal,
               b.name as batter, n.name as non_striker, p.name as bowler, d.name as dismissed,
               f.name as fielder, e.target, e.balls_left_pre
        from ck_events e
        left join ck_players b on b.player_id = e.batter_id
        left join ck_players n on n.player_id = e.non_striker_id
        left join ck_players f on f.player_id = e.fielder_id
        left join ck_players p on p.player_id = e.bowler_id
        left join ck_players d on d.player_id = e.dismissed_id
        where e.match_id in (select unnest(?)) order by e.match_id, e.seq""", [match_ids])


def _innings(ball: dict) -> dict:
    """The announcement as a side comes in: how many balls it has, and its target if it is chasing."""
    return {"kind": "innings", "match_id": ball["match_id"], "innings": ball["innings"],
            "balls": ball.pop("balls_left_pre"), "target": ball.pop("target")}


def messages(con: duckdb.DuckDBPyConnection, match_ids: list[str]) -> Iterator[dict]:
    """Whole matches, one after another: start, then each innings and its balls, then end."""
    opening = starts(con, match_ids)
    current = None
    for ball in balls(con, match_ids):
        innings = (ball["match_id"], ball["innings"])
        if innings != current:
            if current and current[0] != ball["match_id"]:
                yield _end(opening[current[0]])
            if not current or current[0] != ball["match_id"]:
                yield {name: value for name, value in opening[ball["match_id"]].items() if name != "winner"}
            current = innings
            yield _innings(ball)
        else:
            del ball["balls_left_pre"], ball["target"]
        yield ball
    if current:
        yield _end(opening[current[0]])


def _end(start: dict) -> dict:
    return {"kind": "end", "match_id": start["match_id"], "winner": start["winner"]}
