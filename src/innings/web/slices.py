"""A slice of cricket: any filter over every ball, counted as a batting or a bowling line.

One `Slice` holds the filters (who batted, who bowled, against what type, in which phase,
format, league, years, ground, side) and how to split the rows. `run` turns it into one
parameterised query over ck_balls. Matchups, the impact boards and the question box all
come through here, so a number means the same thing wherever it shows.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields

from ..balls import BOWLING_TYPES, TYPE_LABEL
from ..config import CRICKET_FORMATS
from .db import per_database, q

ROLES = ("bat", "bowl")
HANDS = {"L": "Left-handers", "R": "Right-handers"}
FAMILIES = {"pace": "Pace", "spin": "Spin"}
PHASES = {key: label for fmt in CRICKET_FORMATS.values() for key, label, _ in fmt.phases}
PHASE_ORDER = list(dict.fromkeys(key for fmt in CRICKET_FORMATS.values() for key, _, _ in fmt.phases))
CHASE = {"first": "Batting first", "chase": "Chasing"}
MAX_ROWS = 200


@dataclass(frozen=True)
class Slice:
    role: str = "bat"           # whose numbers: the batter's or the bowler's
    batter: str = ""
    bowler: str = ""
    hand: str = ""              # the batter's hand, L or R
    type: str = ""              # the bowler's type, a key of BOWLING_TYPES
    family: str = ""            # pace or spin
    fmt: str = ""
    league: str = ""
    phase: str = ""
    chase: str = ""             # first or chase; limited-overs only
    venue: str = ""
    team: str = ""              # the side of the player whose numbers these are
    opponent: str = ""
    first: int = 0              # first and last year; 0 leaves that end open
    last: int = 0
    by: str = ""                # how to split the rows; "" gives one line
    min: int = -1               # fewest balls a row needs; -1 means the split's default

    def __post_init__(self):
        checks = (("role", ROLES), ("hand", HANDS), ("type", TYPE_LABEL), ("family", FAMILIES),
                  ("fmt", CRICKET_FORMATS), ("phase", PHASES), ("chase", CHASE), ("by", GROUPS))
        for name, allowed in checks:
            value = getattr(self, name)
            if value and value not in allowed:
                raise ValueError(f"{name} cannot be {value!r}")

    def filters(self) -> dict:
        """The fields that narrow the balls, without their defaults."""
        skip = {"role", "by", "min"}
        return {f.name: getattr(self, f.name) for f in fields(self)
                if f.name not in skip and getattr(self, f.name)}

    def own(self) -> str:
        return "batter_id" if self.role == "bat" else "bowler_id"

    def sides(self) -> tuple[str, str]:
        """(this player's side, the other side) as ck_balls columns."""
        return ("bat_team", "field_team") if self.role == "bat" else ("field_team", "bat_team")

    def as_dict(self) -> dict:
        return {key: value for key, value in asdict(self).items() if value not in ("", 0, -1)}


# ---- what is counted ----

# (key, label, digits, SQL). Sums first; the rates are worked out from the sums.
BATTING = (
    ("balls", "Balls", 0, "count(*) filter (where faced)"),
    ("runs", "Runs", 0, "sum(runs_bat)"),
    ("outs", "Out", 0, "count(*) filter (where out)"),
    ("avg", "Avg", 1, "sum(runs_bat) / nullif(count(*) filter (where out), 0)"),
    ("sr", "SR", 1, "100.0 * sum(runs_bat) / nullif(count(*) filter (where faced), 0)"),
    ("fours", "4s", 0, "count(*) filter (where faced and runs_bat = 4)"),
    ("sixes", "6s", 0, "count(*) filter (where faced and runs_bat = 6)"),
    ("dot", "Dot%", 1, "100.0 * count(*) filter (where faced and runs_bat = 0) "
                       "/ nullif(count(*) filter (where faced), 0)"),
    ("rae", "RAE", 1, "sum(bat_rae)"),
    ("rate", "RAE/100", 1, "100.0 * sum(bat_rae) / nullif(count(*) filter (where faced), 0)"),
    ("wpa", "WPA", 2, "sum(wpa)"),
)
BOWLING = (
    ("balls", "Balls", 0, "count(*) filter (where legal)"),
    ("runs", "Runs", 0, "sum(conceded)"),
    ("wkts", "Wkts", 0, "count(*) filter (where bowler_wicket)"),
    ("econ", "Econ", 2, "6.0 * sum(conceded) / nullif(count(*) filter (where legal), 0)"),
    ("avg", "Avg", 1, "sum(conceded) / nullif(count(*) filter (where bowler_wicket), 0)"),
    ("sr", "SR", 1, "count(*) filter (where legal) / nullif(count(*) filter (where bowler_wicket), 0)"),
    ("dot", "Dot%", 1, "100.0 * count(*) filter (where legal and conceded = 0) "
                       "/ nullif(count(*) filter (where legal), 0)"),
    ("xw", "xW", 1, "sum(xw)"),
    ("waa", "W+", 1, "count(*) filter (where bowler_wicket) - sum(xw)"),
    ("rae", "RAE", 1, "sum(bowl_rae)"),
    ("rate", "RAE/100", 1, "100.0 * sum(bowl_rae) / nullif(count(*) filter (where legal), 0)"),
    ("wpa", "WPA", 2, "-sum(wpa)"),
)
COUNTED = {"bat": BATTING, "bowl": BOWLING}


def columns(role: str) -> list[dict]:
    return [dict(key=key, label=label, digits=digits) for key, label, digits, _ in COUNTED[role]]


# ---- how rows are split ----

# split -> (SQL for the row's key, given the slice; fewest balls a row needs by default)
GROUPS = {
    "year": (lambda s: "year", 0),
    "league": (lambda s: "league", 0),
    "fmt": (lambda s: "fmt", 0),
    "phase": (lambda s: "phase", 0),
    "chase": (lambda s: "chase", 0),
    "type": (lambda s: "bowl_type", 0),
    "family": (lambda s: "bowl_family", 0),
    "hand": (lambda s: "hand", 0),
    "venue": (lambda s: "venue", 30),
    "opponent": (lambda s: s.sides()[1], 30),
    "batter": (lambda s: "batter_id", 30),
    "bowler": (lambda s: "bowler_id", 30),
    "player": (lambda s: s.own(), 60),              # one row per player in the slice's role
    "innings": (lambda s: f"{s.own()} || '|' || match_id", 6),   # one player in one match
}


def _where(s: Slice) -> tuple[str, list]:
    mine, theirs = s.sides()
    conditions = {
        "batter": "batter_id = ?", "bowler": "bowler_id = ?", "hand": "hand = ?",
        "type": "bowl_type = ?", "family": "bowl_family = ?", "fmt": "fmt = ?", "league": "league = ?",
        "phase": "phase = ?", "chase": "chase = ?", "venue": "venue = ?",
        "team": f"{mine} = ?", "opponent": f"{theirs} = ?", "first": "year >= ?", "last": "year <= ?",
    }
    chosen = s.filters()
    return " and ".join(["true", *(conditions[name] for name in chosen)]), list(chosen.values())


def _order(s: Slice, rows: list[dict]) -> list[dict]:
    if s.by == "year":
        return sorted(rows, key=lambda row: -int(row["key"]))
    fixed = {"phase": PHASE_ORDER, "type": [key for key, _, _ in BOWLING_TYPES],
             "family": list(FAMILIES), "hand": list(HANDS), "chase": list(CHASE)}.get(s.by)
    if fixed:
        return sorted(rows, key=lambda row: fixed.index(row["key"]) if row["key"] in fixed else 99)
    return rows   # already by balls, most first


def _labels(s: Slice, keys: list[str]) -> dict[str, str]:
    """A readable name for each row key."""
    named = {"phase": PHASES, "type": TYPE_LABEL, "family": FAMILIES, "hand": HANDS, "chase": CHASE}
    if s.by in named:
        return {key: named[s.by].get(key, "Not known") for key in keys}
    if s.by in ("batter", "bowler", "player"):
        return _player_names(keys)
    if s.by == "innings":
        return _innings_names(keys)
    return {key: str(key) for key in keys}


def _player_names(ids: list[str]) -> dict[str, str]:
    if not ids:
        return {}
    rows = q("select player_id, name from players where sport = 'ck' and player_id in "
             f"({', '.join('?' * len(ids))})", ids)
    return {row["player_id"]: row["name"] for row in rows}


def _innings_names(keys: list[str]) -> dict[str, str]:
    pairs = [key.split("|", 1) for key in keys]
    names = _player_names(sorted({player for player, _ in pairs}))
    match_ids = sorted({match for _, match in pairs})
    games = {row["match_id"]: row for row in q(
        "select match_id, date, team1, team2 from matches where sport = 'ck' and match_id in "
        f"({', '.join('?' * len(match_ids))})", match_ids)} if match_ids else {}
    labels = {}
    for key, (player, match) in zip(keys, pairs, strict=True):
        game = games.get(match)
        where = f"{game['team1']} v {game['team2']}, {game['date']:%d %b %Y}" if game else match
        labels[key] = f"{names.get(player, player)} · {where}"
    return labels


def run(s: Slice, sort: str = "") -> dict:
    """The slice's total line and, if it is split, one line per part."""
    counted = COUNTED[s.role]
    select = ", ".join(f"{sql} as {key}" for key, _, _, sql in counted)
    where, params = _where(s)
    total = q(f"select {select} from ck_balls where {where}", params)[0]
    rows: list[dict] = []
    floor = 0
    if s.by:
        key_sql, default_floor = GROUPS[s.by]
        floor = default_floor if s.min < 0 else s.min
        order = sort if sort in {key for key, *_ in counted} else "balls"
        balls = next(sql for key, _, _, sql in counted if key == "balls")
        rows = q(f"""select {key_sql(s)} as key, {select} from ck_balls
                     where {where} and {key_sql(s)} is not null
                     group by all having {balls} >= ?
                     order by {order} desc nulls last, key limit {MAX_ROWS}""", [*params, floor])
        labels = _labels(s, [row["key"] for row in rows])
        rows = [dict(row, label=labels[row["key"]]) for row in (rows if sort else _order(s, rows))]
    estimated = None
    if s.family or s.by == "family":       # how much of the answer rests on estimates
        estimated = q(f"""select avg(family_estimated::int) as share from ck_balls
                          where {where} and bowl_family is not null""", params)[0]["share"]
    named = _player_names([player for player in (s.batter, s.bowler) if player])
    return dict(slice=s.as_dict(), title=describe(s), columns=columns(s.role), total=total, rows=rows,
                min=floor, names=dict(batter=named.get(s.batter), bowler=named.get(s.bowler)),
                coverage=coverage(), estimated=estimated)


@per_database()
def coverage() -> dict:
    """The share of balls whose bowler's type, pace or spin, and batter's hand we know, and
    how well the pace-or-spin estimates did on bowlers whose style was known."""
    row = q("""select count(*) as n, count(bowl_type) as typed, count(hand) as handed,
                      count(bowl_family) as family from ck_balls""")[0]
    sure = q("select value from constants where sport = 'ck' and name = 'pace_spin_sure_accuracy'")
    return dict(type=row["typed"] / row["n"], hand=row["handed"] / row["n"],
                family=row["family"] / row["n"], estimate_accuracy=sure[0]["value"] if sure else None)


# ---- in words ----

def describe(s: Slice) -> str:
    """The slice as a heading: "Virat Kohli batting against leg-spin · death overs · IPL 2024"."""
    names = _player_names([player for player in (s.batter, s.bowler) if player])
    bowler_words = [TYPE_LABEL[s.type]] if s.type else [FAMILIES[s.family]] if s.family else []
    batter_words = [HANDS[s.hand]] if s.hand else []
    if s.role == "bat":
        subject, versus, own, theirs, doing = s.batter, s.bowler, batter_words, bowler_words, "batting"
    else:
        subject, versus, own, theirs, doing = s.bowler, s.batter, bowler_words, batter_words, "bowling"
    # "Virat Kohli batting", or with no player named, "Left-handers batting" / "Spin bowling".
    head = f"{names.get(subject, subject)} {doing}" if subject else (own[0] if own else doing.title())
    if not subject and own:
        head += f" {doing}"
    against = [names[versus]] if versus else []
    against += [word.lower() for word in theirs] + ([s.opponent] if s.opponent else [])
    parts = [head + (" against " + ", ".join(against) if against else "")]
    if s.team:
        parts.append(f"for {s.team}")
    if s.phase:
        overs = " overs" if s.phase in ("middle", "death") else ""
        parts.append(PHASES[s.phase].split(" (")[0].lower() + overs)
    if s.chase:
        parts.append(CHASE[s.chase].lower())
    if s.fmt and not s.league:
        parts.append(s.fmt)
    if s.league:
        parts.append(s.league)
    if s.first or s.last:
        parts.append(_years(s.first, s.last))
    if s.venue:
        parts.append(f"at {s.venue}")
    return " · ".join(parts)


def _years(first: int, last: int) -> str:
    if first and first == last:
        return str(first)
    if first and last:
        return f"{first}–{last}"
    return f"since {first}" if first else f"up to {last}"
