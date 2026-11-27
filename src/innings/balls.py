"""ck_styles and ck_balls: the tables behind matchups, impact and the question box.

ck_styles says how each player bats (left or right hand) and bowls (one of six types),
read from the Wikipedia infobox text in data/raw/styles.csv. A short hand-written list
(`styles_known.csv`, next to this file) fills in players the infoboxes miss.

ck_balls is one row per ball with everything a slice can filter or count, already
joined: the match's year, league and ground (the venue without its town), the phase of
the innings, both players' styles, and the bowler's expected wickets for that ball.
Slices read only this table. `out` is the striker's own dismissal: a non-striker run
out is nobody's matchup.
"""
from __future__ import annotations

import csv
from pathlib import Path

import duckdb

from .config import CRICKET_FORMATS
from .ingest.styles import STYLES, plain

KNOWN = Path(__file__).with_name("styles_known.csv")

# (key, label, family). Order is the order tables list them.
BOWLING_TYPES = (
    ("right-pace", "Right-arm pace", "pace"),
    ("left-pace", "Left-arm pace", "pace"),
    ("off-spin", "Off-spin", "spin"),
    ("leg-spin", "Leg-spin", "spin"),
    ("left-orthodox", "Left-arm orthodox", "spin"),
    ("left-wrist", "Left-arm wrist-spin", "spin"),
)
TYPE_LABEL = {key: label for key, label, _ in BOWLING_TYPES}
TYPE_FAMILY = {key: family for key, _, family in BOWLING_TYPES}
PACE_WORDS = ("fast", "medium", "seam", "swing", "pace")


def _one_style(words: str) -> str | None:
    """One bowling style in words, as an infobox writes it, -> a type key."""
    s = words.lower().replace("-", " ")
    left = "left" in s
    if left and any(w in s for w in ("unorthodox", "chinaman", "wrist")):
        return "left-wrist"
    if "googly" in s or ("leg" in s and ("break" in s or "spin" in s)):
        return "left-wrist" if left else "leg-spin"
    if "orthodox" in s or (left and ("spin" in s or "slow" in s) and "medium" not in s):
        return "left-orthodox"
    if "off" in s and ("break" in s or "spin" in s):
        return "off-spin"
    if any(w in s for w in PACE_WORDS):
        return "left-pace" if left else "right-pace"
    return None


def bowling_type(words: str) -> str | None:
    """A player's main bowling type: the first style the infobox lists that we recognise."""
    for part in words.replace(";", ",").replace("/", ",").replace(" and ", ",").split(","):
        found = _one_style(part)
        if found:
            return found
    return None


def batting_hand(words: str) -> str | None:
    s = words.lower()
    return "L" if "left" in s else "R" if "right" in s else None


def _style_rows() -> list[tuple[str, str | None, str | None]]:
    """(player_id, hand, bowling type) for everyone we know anything about."""
    rows: dict[str, tuple[str | None, str | None]] = {}
    if STYLES.exists():
        with open(STYLES, newline="") as f:
            for row in csv.DictReader(f):
                rows[row["player_id"]] = (batting_hand(plain(row["batting"])),
                                          bowling_type(plain(row["bowling"])))
    with open(KNOWN, newline="") as f:
        for row in csv.DictReader(line for line in f if not line.startswith("#")):
            hand, kind = rows.get(row["player_id"], (None, None))
            rows[row["player_id"]] = (row["hand"] or hand, row["type"] or kind)
    return [(player, hand, kind) for player, (hand, kind) in sorted(rows.items()) if hand or kind]


def _build_styles(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("create or replace table ck_styles (player_id varchar, hand varchar, bowl_type varchar)")
    rows = _style_rows()
    if rows:                                 # none before the first download
        con.executemany("insert into ck_styles values (?, ?, ?)", rows)


def phase_key() -> str:
    """SQL naming the phase of a ball (`powerplay`, `middle`, `death` or a Test's ball age)."""
    def one_format(fmt) -> str:
        branches = [f"""when "over" < {end} then '{key}'""" for key, _, end in fmt.phases[:-1]]
        return f"case {' '.join(branches)} else '{fmt.phases[-1][0]}' end"
    branches = [f"when e.fmt = '{fmt.name}' then {one_format(fmt)}" for fmt in CRICKET_FORMATS.values()]
    return f"case {' '.join(branches)} end"


def _build_balls(con: duckdb.DuckDBPyConnection) -> None:
    # Expected wickets: how often the bowler takes a wicket on a ball like this one, in the
    # same kind of cricket (men's or women's, format), over and wickets down. Test overs past
    # the 100th are pooled: the ball is changed at 80 and few innings get that far.
    con.execute(f"""
        create or replace table ck_balls as
        with balls as (
            select e.*, m.year, m.league, split_part(m.venue, ',', 1) as venue, c.gender,
                   least(e."over", 100) as over_bucket, {phase_key()} as phase
            from ck_ev e
            join matches m on m.sport = 'ck' and m.match_id = e.match_id
            join ck_matches c on c.match_id = e.match_id
        ), rates as (
            select gender, fmt, over_bucket, wkts_pre, avg(bowler_wicket::int) as xw
            from balls group by all
        )
        select b.match_id, b.year, b.league, b.fmt, b.venue,
               case when b.fmt = 'Test' then null when b.innings = 1 then 'first' else 'chase' end
                   as chase,
               b.phase, b.bat_team, b.field_team, b.batter_id, b.bowler_id,
               bat.hand as hand, bowl.bowl_type as bowl_type,
               case when bowl.bowl_type like '%pace' then 'pace' when bowl.bowl_type is not null
                    then 'spin' end as bowl_family,
               not b.wide as faced, not b.wide and not b.noball as legal,
               b.runs_bat, b.runs - b.byes as conceded,
               coalesce(b.dismissed_id = b.batter_id, false) as out, b.bowler_wicket,
               b.bat_rae, b.bowl_rae, b.wpa, r.xw
        from balls b
        join rates r using (gender, fmt, over_bucket, wkts_pre)
        left join ck_styles bat on bat.player_id = b.batter_id
        left join ck_styles bowl on bowl.player_id = b.bowler_id
        order by b.match_id, b.seq
    """)


def build(con: duckdb.DuckDBPyConnection) -> None:
    _build_styles(con)
    _build_balls(con)
