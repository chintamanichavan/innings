"""The question box: plain words -> a Slice.

"Bumrah death overs IPL 2024" or "Kohli vs leg spin since 2020". The reader looks for the
longest known phrase at each place in the question: a player, team, ground, league,
format, phase, bowling type, batting hand, year or a word that says how to split the
rows. Every phrase it used is reported back, so a reader sees how they were understood,
and so are the words it could not place.

No language model: a fixed vocabulary, so the same words always give the same answer.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field

from ..balls import TYPE_LABEL
from ..ingest.styles import STYLES
from .db import per_database, q
from .players import main_role
from .slices import CHASE, FAMILIES, HANDS, PHASES, Slice

LONGEST = 6                 # words in the longest phrase looked for
SURNAME_FLOOR = 300         # balls a player needs before their surname alone finds them

# Words that carry no meaning of their own here.
FILLER = {
    "a", "an", "the", "in", "at", "on", "of", "for", "and", "with", "how", "does", "did", "do",
    "is", "was", "are", "what", "whats", "his", "her", "their", "stats", "stat", "record",
    "records", "numbers", "figures", "career", "overs", "over", "matchup", "matchups", "when",
    "show", "me", "biggest", "greatest", "has", "have", "had", "took", "taken", "scored", "made",
}
VERSUS = {"vs", "v", "versus", "against", "facing"}
SINCE = {"since", "from", "after"}
UNTIL = {"until", "till", "before", "upto"}

# phrase -> (what it sets, value). Several phrases can mean the same thing.
FIXED: dict[str, tuple[str, str]] = {
    "batting": ("role", "bat"), "batter": ("role", "bat"), "batsman": ("role", "bat"),
    "bowling": ("role", "bowl"), "bowler": ("role", "bowl"), "bowlers": ("role", "bowl"),
    "batters": ("role", "bat"), "batsmen": ("role", "bat"),
    "powerplay": ("phase", "powerplay"), "pp": ("phase", "powerplay"),
    "middle": ("phase", "middle"), "death": ("phase", "death"), "new ball": ("phase", "new-ball"),
    "old ball": ("phase", "old-ball"), "second new ball": ("phase", "second-new-ball"),
    "t20": ("fmt", "T20"), "t20s": ("fmt", "T20"), "odi": ("fmt", "ODI"), "odis": ("fmt", "ODI"),
    "test": ("fmt", "Test"), "tests": ("fmt", "Test"),
    "chasing": ("chase", "chase"), "chase": ("chase", "chase"), "batting first": ("chase", "first"),
    "defending": ("chase", "first"),
    "pace": ("family", "pace"), "pacers": ("family", "pace"), "seam": ("family", "pace"),
    "seamers": ("family", "pace"), "fast bowling": ("family", "pace"), "quicks": ("family", "pace"),
    "spin": ("family", "spin"), "spinners": ("family", "spin"),
    "leg spin": ("type", "leg-spin"), "legspin": ("type", "leg-spin"), "leg spinners": ("type", "leg-spin"),
    "leggies": ("type", "leg-spin"), "wrist spin": ("type", "leg-spin"),
    "off spin": ("type", "off-spin"), "offspin": ("type", "off-spin"), "off spinners": ("type", "off-spin"),
    "finger spin": ("type", "off-spin"),
    "left arm spin": ("type", "left-orthodox"), "left arm orthodox": ("type", "left-orthodox"),
    "left arm spinners": ("type", "left-orthodox"),
    "chinaman": ("type", "left-wrist"), "left arm wrist spin": ("type", "left-wrist"),
    "left arm pace": ("type", "left-pace"), "left arm seam": ("type", "left-pace"),
    "left arm fast": ("type", "left-pace"), "left arm quicks": ("type", "left-pace"),
    "right arm pace": ("type", "right-pace"), "right arm seam": ("type", "right-pace"),
    "right arm fast": ("type", "right-pace"),
    "left handers": ("hand", "L"), "left handed": ("hand", "L"), "lefties": ("hand", "L"),
    "lefthanders": ("hand", "L"), "left hand batters": ("hand", "L"),
    "right handers": ("hand", "R"), "right handed": ("hand", "R"), "righthanders": ("hand", "R"),
    "by year": ("by", "year"), "each year": ("by", "year"), "per year": ("by", "year"),
    "by season": ("by", "year"), "each season": ("by", "year"), "year by year": ("by", "year"),
    "by phase": ("by", "phase"), "by venue": ("by", "venue"), "by ground": ("by", "venue"),
    "grounds": ("by", "venue"), "venues": ("by", "venue"), "by league": ("by", "league"),
    "by format": ("by", "fmt"), "by type": ("by", "type"), "by bowling type": ("by", "type"),
    "by team": ("by", "opponent"), "by opponent": ("by", "opponent"), "teams": ("by", "opponent"),
    "by bowler": ("by", "bowler"), "each bowler": ("by", "bowler"), "by batter": ("by", "batter"),
    "each batter": ("by", "batter"), "by hand": ("by", "hand"),
    "innings": ("by", "innings"), "knocks": ("by", "innings"), "spells": ("by", "innings"),
    "biggest innings": ("by", "innings"),
    "runs": ("sort", "runs"), "sixes": ("sort", "sixes"), "fours": ("sort", "fours"),
    "strike rate": ("sort", "sr"), "wickets": ("sort", "wkts"), "impact": ("sort", "wpa"),
    "wpa": ("sort", "wpa"), "runs added": ("sort", "rae"), "rae": ("sort", "rae"),
    "wickets above average": ("sort", "waa"),
    "best": ("by", "player"), "top": ("by", "player"), "most": ("by", "player"),
    "leaders": ("by", "player"), "leaderboard": ("by", "player"), "who": ("by", "player"),
}
LEAGUES = {"ipl": "IPL", "bbl": "BBL", "big bash": "BBL", "psl": "PSL", "cpl": "CPL", "sa20": "SA20",
           "t20i": "T20I", "t20is": "T20I", "womens t20i": "T20I (W)", "womens odi": "ODI (W)"}
# Short names fans use for sides. Others are found by their full name.
CODES = {"csk": "Chennai Super Kings", "mi": "Mumbai Indians", "rcb": "Royal Challengers Bengaluru",
         "kkr": "Kolkata Knight Riders", "srh": "Sunrisers Hyderabad", "dc": "Delhi Capitals",
         "pbks": "Punjab Kings", "rr": "Rajasthan Royals", "gt": "Gujarat Titans",
         "lsg": "Lucknow Super Giants", "ind": "India", "aus": "Australia", "eng": "England",
         "pak": "Pakistan", "nz": "New Zealand", "sl": "Sri Lanka", "wi": "West Indies",
         "ban": "Bangladesh", "afg": "Afghanistan", "rsa": "South Africa"}
GROUND_ENDINGS = (" international cricket stadium", " cricket stadium", " cricket ground",
                  " stadium", " ground")


BOWLING_SORTS = {"wkts", "waa"}     # sorting by these means the question is about bowlers


@dataclass
class Reading:
    slice: Slice
    sort: str = ""                                          # a column to rank by, if asked
    understood: list[dict] = field(default_factory=list)   # {text, means} for each phrase used
    unknown: list[str] = field(default_factory=list)


def words_of(text: str) -> list[str]:
    """Lower case, punctuation and apostrophes gone, hyphens as spaces, ranges kept: 2020-2024."""
    text = re.sub(r"(\d{4})\s*(?:-|–|to)\s*(\d{4})", r"\1~\2", text.lower())
    text = text.replace("'", "").replace("’", "")
    return re.sub(r"[^a-z0-9~]+", " ", text).split()


def _plain(name: str) -> str:
    return " ".join(words_of(name))


@per_database()
def vocabulary() -> dict[str, tuple[str, str, str]]:
    """phrase -> (kind, value, what to call it). Built once per database."""
    found: dict[str, tuple[str, str, str]] = {}
    players = q("""select player_id, name, n from players where sport = 'ck' and n > 0
                   order by n desc, player_id""")
    for row in players:                                     # most balls first: they keep a shared name
        found.setdefault(_plain(row["name"]), ("player", row["player_id"], row["name"]))
    name_of = {row["player_id"]: row["name"] for row in players}
    for player, article in _articles():                     # "Harshal Patel" for "HV Patel"
        if player in name_of:
            found.setdefault(_plain(article), ("player", player, name_of[player]))
    for row in players:
        if row["n"] >= SURNAME_FLOOR:
            found.setdefault(_plain(row["name"]).split()[-1], ("player", row["player_id"], row["name"]))
    for venue in (row["venue"] for row in q("select distinct venue from ck_balls order by 1")):
        found.setdefault(_plain(venue), ("venue", venue, venue))
        for ending in GROUND_ENDINGS:
            short = _plain(venue).removesuffix(ending.strip()).strip()
            if short != _plain(venue) and len(short) > 3:
                found.setdefault(short, ("venue", venue, venue))
    # A town finds its busiest ground: "Ahmedabad" -> Narendra Modi Stadium.
    for row in q("""select split_part(venue, ', ', 2) as town, mode(split_part(venue, ',', 1)) as ground
                    from matches where venue like '%, %' group by 1"""):
        found.setdefault(_plain(row["town"]), ("venue", row["ground"], row["ground"]))
    for row in q("select distinct team1 as team from matches union select team2 from matches"):
        found[_plain(row["team"])] = ("team", row["team"], row["team"])
    found |= {code: ("team", team, team) for code, team in CODES.items()}
    found |= {words: ("league", league, league) for words, league in LEAGUES.items()}
    found |= {words: (kind, value, _meaning(kind, value)) for words, (kind, value) in FIXED.items()}
    return found


def _articles() -> list[tuple[str, str]]:
    """(player id, Wikipedia article title without its "(cricketer)" note)."""
    if not STYLES.exists():
        return []
    with open(STYLES, newline="") as f:
        return [(row["player_id"], re.sub(r"\s*\(.*\)$", "", row["article"]))
                for row in csv.DictReader(f) if row["article"]]


def _meaning(kind: str, value: str) -> str:
    named = {"phase": PHASES, "type": TYPE_LABEL, "family": FAMILIES, "hand": HANDS, "chase": CHASE,
             "role": {"bat": "Batting", "bowl": "Bowling"}}
    if kind in named:
        return named[kind][value]
    return {"by": "Split by " + value, "sort": "Ranked by " + value}.get(kind, value)


def _phrases(words: list[str]) -> list[tuple[str, tuple[str, str, str] | None]]:
    """The question cut into the longest known phrases; an unknown word stands alone."""
    known = vocabulary()
    cut, at = [], 0
    while at < len(words):
        for size in range(min(LONGEST, len(words) - at), 0, -1):
            phrase = " ".join(words[at:at + size])
            if phrase in known:
                cut.append((phrase, known[phrase]))
                at += size
                break
        else:
            cut.append((words[at], None))
            at += 1
    return cut


def _years(word: str, mode: str) -> tuple[int, int] | None:
    """A year or a range of years, read with "since" or "until" if one came just before."""
    parts = [int(part) for part in word.split("~") if part.isdigit() and len(part) == 4]
    if not parts or not all(1990 < year < 2100 for year in parts):
        return None
    if len(parts) == 2:
        return min(parts), max(parts)
    return {"since": (parts[0], 0), "until": (0, parts[0])}.get(mode, (parts[0], parts[0]))


def read(question: str) -> Reading:
    """Read a question into a slice. Words that mean nothing here are listed as unknown."""
    chosen: dict = {}
    styles: list[str] = []                    # "hand" or "type", in the order they were named
    players: list[tuple[str, bool]] = []      # (player id, came after "vs")
    understood, unknown = [], []
    versus, mode = False, ""
    for phrase, meaning in _phrases(words_of(question)):
        if meaning is None:
            years = _years(phrase, mode)
            if years:
                chosen["first"], chosen["last"] = years
                understood.append(dict(text=phrase.replace("~", "–"), means=_year_words(*years)))
            elif phrase in VERSUS:
                versus = True
            elif phrase in SINCE or phrase in UNTIL:
                mode = "since" if phrase in SINCE else "until"
                continue
            elif phrase not in FILLER:
                unknown.append(phrase)
            mode = ""
            continue
        kind, value, label = meaning
        if kind == "player":
            players.append((value, versus))
        elif kind == "team":
            chosen["opponent" if versus or "team" in chosen else "team"] = value
        else:
            chosen[kind] = value
        if kind in ("hand", "type", "family"):
            styles.append("hand" if kind == "hand" else "type")
        means = {"player": "Player", "team": "Opponent" if versus else "Team", "venue": "Ground",
                 "league": "League"}.get(kind)
        understood.append(dict(text=phrase, means=f"{means}: {label}" if means else label))
        mode = ""
    sort = chosen.pop("sort", "")
    if sort in BOWLING_SORTS:
        chosen.setdefault("role", "bowl")
    if "chase" in chosen:
        chosen.setdefault("role", "bat")                   # chasing is something batters do
    _place_players(chosen, players, styles)
    _choose_split(chosen)
    if not sort and chosen["by"] in ("player", "innings"):
        sort = "wpa" if chosen["by"] == "innings" else "rae"
    return Reading(Slice(**chosen), sort, understood, unknown)


def _year_words(first: int, last: int) -> str:
    if first == last:
        return f"Year: {first}"
    return f"Years: {first}–{last}" if first and last else (f"Since {first}" if first else f"Up to {last}")


def _place_players(chosen: dict, players: list[tuple[str, bool]], styles: list[str]) -> None:
    """The first player named is the one whose numbers these are; the next is the opponent.
    With no player, the first style named says whose numbers: "left handers vs leg spin" is
    batting, "spinners in the powerplay" is bowling."""
    if not players:
        if styles:
            chosen.setdefault("role", "bat" if styles[0] == "hand" else "bowl")
        return
    subject = players[0][0]
    role = chosen.get("role") or main_role("ck", subject)
    if "hand" in chosen and "role" not in chosen:
        role = "bowl"                                       # "Bumrah v left handers"
    if ("type" in chosen or "family" in chosen) and "role" not in chosen:
        role = "bat"                                        # "Kohli v leg spin"
    chosen["role"] = role
    chosen["batter" if role == "bat" else "bowler"] = subject
    if len(players) > 1:
        chosen["bowler" if role == "bat" else "batter"] = players[1][0]


def _choose_split(chosen: dict) -> None:
    """When the question does not say how to split: a player's numbers go year by year,
    or by bowling type for one year; with no player, it is a leaderboard."""
    if "by" in chosen:
        return
    player = chosen.get("batter") or chosen.get("bowler")
    one_year = chosen.get("first") and chosen.get("first") == chosen.get("last")
    if not player:
        chosen["by"] = "player"
    elif chosen.get("batter") and chosen.get("bowler"):
        chosen["by"] = "year"
    elif one_year:
        chosen["by"] = "type" if chosen.get("role") == "bat" else "hand"
    else:
        chosen["by"] = "year"


EXAMPLES = (
    "Kohli vs leg spin",
    "Bumrah death overs IPL 2024",
    "Rashid Khan vs left handers",
    "best death bowlers IPL 2025",
    "spinners in the powerplay BBL",
    "Buttler chasing since 2022",
    "Rohit Sharma at Wankhede",
    "biggest innings T20I 2024",
)
