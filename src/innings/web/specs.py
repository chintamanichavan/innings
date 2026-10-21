"""What a stat table looks like, for each sport and role.

One `Spec` says which season table to read, what counts as an opportunity, which
columns to add up, which rates to derive from the sums, and what the page shows.
Everything that lists players reads its columns from here.
"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException

from .db import q


@dataclass(frozen=True)
class Spec:
    table: str
    opps: str                       # the column that counts opportunities
    floor: int                      # opportunities needed to appear on a leaderboard
    sums: tuple[str, ...]           # columns added up as they are
    derived: dict[str, str]         # name -> SQL over the summed rows
    shown: tuple[tuple[str, str, int], ...]   # (key, label, digits) in display order

    def select(self) -> str:
        parts = [f"sum({c}) as {c}" for c in self.sums]
        parts += [f"{expr} as {name}" for name, expr in self.derived.items()]
        return ", ".join(parts)

    def columns(self) -> list[dict]:
        return [dict(key=key, label=label, digits=digits) for key, label, digits in self.shown]

    def sortable(self) -> set[str]:
        return {key for key, _, _ in self.shown}


SPORTS = ("ck",)


def rate(top: str, bottom: str, scale: float = 1) -> str:
    return f"{scale} * sum({top}) / nullif(sum({bottom}), 0)"


VALUE = (("rae", "RAE", 1), ("wpa", "WPA", 2), ("clutch", "Clutch", 2))

SPECS = {
    ("ck", "bat"): Spec(
        table="ck_bat", opps="balls", floor=100,
        sums=("inns", "runs", "balls", "outs", "fours", "sixes", "rae", "wpa", "clutch"),
        derived={"avg": rate("runs", "outs"), "sr": rate("runs", "balls", 100),
                 "rate": rate("rae", "balls", 100)},
        shown=(("inns", "Inn", 0), ("runs", "Runs", 0), ("balls", "Balls", 0), ("outs", "Out", 0),
               ("avg", "Avg", 1), ("sr", "SR", 1), ("fours", "4s", 0), ("sixes", "6s", 0),
               VALUE[0], ("rate", "RAE/100", 1), *VALUE[1:]),
    ),
    ("ck", "bowl"): Spec(
        table="ck_bowl", opps="balls", floor=100,
        sums=("inns", "balls", "runs", "wkts", "rae", "wpa", "clutch"),
        derived={"econ": rate("runs", "balls", 6), "avg": rate("runs", "wkts"),
                 "sr": rate("balls", "wkts"), "dot": rate("dots", "balls", 100),
                 "rate": rate("rae", "balls", 100)},
        shown=(("inns", "Inn", 0), ("balls", "Balls", 0), ("runs", "Runs", 0), ("wkts", "Wkts", 0),
               ("econ", "Econ", 2), ("avg", "Avg", 1), ("sr", "SR", 1), ("dot", "Dot%", 1),
               VALUE[0], ("rate", "RAE/100", 1), *VALUE[1:]),
    ),
}


def known_sport(sport: str | None = None) -> None:
    """A dependency for routes that take a sport, in the path or the query: only cricket exists."""
    if sport is not None and sport not in SPORTS:
        raise HTTPException(404, "unknown sport")


def spec_for(sport: str, role: str) -> Spec:
    if (sport, role) not in SPECS:
        raise HTTPException(404, "unknown sport or role")
    return SPECS[(sport, role)]


def season_lines(spec: Spec, player_id: str) -> list[dict]:
    """One row per year and league, newest first."""
    return q(f"""select year, league, arg_max(team, year) as team, {spec.select()}
                 from {spec.table} where player_id = ? group by year, league
                 order by year desc, sum({spec.opps}) desc""", [player_id])


def career_line(spec: Spec, player_id: str) -> dict:
    return q(f"select {spec.select()} from {spec.table} where player_id = ?", [player_id])[0]
