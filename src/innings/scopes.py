"""SQL fragments that pick out a slice of cricket. They are written against a season
table (ck_bat, ck_bowl), which has `league` and `team` columns."""
from __future__ import annotations

from .config import FULL_MEMBERS, INTERNATIONAL

_members = ", ".join(f"'{nation}'" for nation in sorted(FULL_MEMBERS))
_not_international = " and ".join(f"league not like '{name}%'" for name in INTERNATIONAL)

# Cricket against strong opposition: franchise leagues, and internationals for a full member.
MAJOR_CRICKET = f"({_not_international} or replace(team, ' (W)', '') in ({_members}))"

# The format a league is played in. Every franchise league we load is T20.
FORMAT_OF_LEAGUE = ("case when league like 'ODI%' then 'ODI' "
                    "when league like 'Test%' then 'Test' else 'T20' end")


def in_format(fmt: str) -> str:
    """Major cricket in one format."""
    return f"{MAJOR_CRICKET} and {FORMAT_OF_LEAGUE} = '{fmt}'"
