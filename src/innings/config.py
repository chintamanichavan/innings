"""Where things live, what data to load, and the shape of each cricket format."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(os.environ.get("INNINGS_HOME", Path(__file__).resolve().parents[2]))
DATA = ROOT / "data"
RAW = DATA / "raw"
DB_PATH = DATA / "innings.duckdb"
SEASON = DATA / "season"   # what the season simulation leaves for the site to show
PORT = 8453


@dataclass(frozen=True)
class CricketFormat:
    name: str
    balls: int | None                           # balls in a full innings; None means no limit
    phases: tuple[tuple[str, int | None], ...]  # (label, first over after the phase); None ends the last
    profile_floor: int                          # career balls needed for a skill profile


CRICKET_FORMATS = {
    "T20": CricketFormat(
        "T20", 120, (("Powerplay (overs 1-6)", 6), ("Middle (7-15)", 15), ("Death (16-20)", None)),
        profile_floor=500),
    "ODI": CricketFormat(
        "ODI", 300, (("Powerplay (overs 1-10)", 10), ("Middle (11-40)", 40), ("Death (41-50)", None)),
        profile_floor=1000),
    "Test": CricketFormat(
        "Test", None,
        (("New ball (overs 1-20)", 20), ("Old ball (21-80)", 80), ("Second new ball (81+)", None)),
        profile_floor=2000),
}
CK_BALLS = {name: fmt.balls for name, fmt in CRICKET_FORMATS.items()}

# Cricsheet archives to load: archive code -> (competition label, format).
CK_ARCHIVES = {
    "ipl": ("IPL", "T20"),
    "bbl": ("BBL", "T20"),
    "psl": ("PSL", "T20"),
    "cpl": ("CPL", "T20"),
    "sat": ("SA20", "T20"),
    "t20s": ("T20I", "T20"),
    "odis": ("ODI", "ODI"),
    "tests": ("Test", "Test"),
}
INTERNATIONAL = ("T20I", "ODI", "Test")   # league names start with one of these for national sides

# ICC full members. Ratings cannot compare teams that never meet, so international
# tables show these nations unless asked for everyone.
FULL_MEMBERS = {
    "Afghanistan", "Australia", "Bangladesh", "England", "India", "Ireland",
    "New Zealand", "Pakistan", "South Africa", "Sri Lanka", "West Indies", "Zimbabwe",
}
