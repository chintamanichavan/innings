"""The forecaster's record: every call, scored by one rule."""
from __future__ import annotations

from . import matches
from .db import per_database, q

SERIES_POINTS = 300


def points(p: float, won: bool) -> float:
    """The scoring rule. A coin flip scores 0, a sure and right call scores 25, a sure and
    wrong call scores -75."""
    return 25 - 100 * (p - (1.0 if won else 0.0)) ** 2


def _score(call: dict) -> dict:
    """Add the verdict and the points to one call."""
    first_won = call["winner"] == call["team1"]
    favoured_first = call["p1"] >= 0.5
    call["date"] = str(call["date"])
    call["right"] = favoured_first == first_won
    call["points"] = points(call["p1"], first_won)
    call["pick"] = call["team1"] if favoured_first else call["team2"]
    call["conf"] = max(call["p1"], 1 - call["p1"])
    return call


@per_database(max_entries=4)
def _tested(sport: str) -> tuple[dict, ...]:
    """Calls made from earlier data, on seasons the model never trained on."""
    rows = q(f"""select m.match_id as id, m.date, m.year, m.league, m.team1, m.team2, m.winner,
                        p.p_full as p1, {matches.MAJOR} as major
                 from predictions p join matches m using (sport, match_id)
                 where p.sport = ? and m.winner is not null""", [sport])
    return tuple(_score(r) for r in rows)


def calls(sport: str) -> list[dict]:
    """Every scored call for a sport, oldest first."""
    return sorted(_tested(sport), key=lambda r: (r["date"], str(r["id"])))


def tally(rows: list[dict]) -> dict:
    n, points = len(rows), sum(r["points"] for r in rows)
    return dict(n=n, right=sum(r["right"] for r in rows), points=points, per_call=points / n if n else 0.0)


def tally_by(rows: list[dict], key: str) -> list[dict]:
    """One tally per league or year. Leagues come biggest first, years newest first."""
    groups: dict = {}
    for row in rows:
        groups.setdefault(row[key], []).append(row)
    out = [dict(tally(group), **{key: value}) for value, group in groups.items()]
    by_size = key == "league"
    return sorted(out, key=lambda t: -t["n"] if by_size else -t[key])


def running_total(rows: list[dict]) -> list[dict]:
    total, series = 0.0, []
    for row in rows:
        total += row["points"]
        series.append(dict(date=row["date"], value=total))
    step = max(1, len(series) // SERIES_POINTS)
    return series[::step] + series[-1:]


def worst_misses(rows: list[dict], count: int = 8) -> list[dict]:
    wrong = [r for r in rows if not r["right"]]
    return sorted(wrong, key=lambda r: -r["conf"])[:count]
