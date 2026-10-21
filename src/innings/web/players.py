"""Players: skill profiles and the extra detail on a player page."""
from __future__ import annotations

from ..insights import DIMS
from . import stories
from .db import q
from .specs import spec_for

SERIES_POINTS = 300   # enough to draw a career line; more only slows the page


def name_of(sport: str, player_id: str) -> str | None:
    rows = q("select name from players where sport = ? and player_id = ?", [sport, player_id])
    return rows[0]["name"] if rows else None


def main_role(sport: str, player_id: str) -> str:
    """Whether a player mostly bats or mostly bowls, by opportunities."""
    row = q("""select sum(bat_n) as bat, sum(bowl_n) as bowl from player_match
               where sport = ? and player_id = ?""", [sport, player_id])[0]
    return "bat" if (row["bat"] or 0) >= (row["bowl"] or 0) else "bowl"


def profiles(sport: str, player_id: str) -> list[dict]:
    """Every skill profile a player qualifies for, biggest sample first."""
    rows = q("select * from profiles where sport = ? and player_id = ? order by n desc", [sport, player_id])
    return [dict(role=r["role"], fmt=r["fmt"], n=r["n"],
                 dims=[dict(label=label, pct=r[f"d{i}"]) for i, label in enumerate(DIMS[r["role"]], start=1)])
            for r in rows]


def primary(all_profiles: list[dict]) -> dict[str, dict]:
    """One profile per role: the format the player has played most."""
    first: dict[str, dict] = {}
    for profile in all_profiles:
        first.setdefault(profile["role"], profile)
    return first


def _game_log(sport: str, player_id: str) -> list[dict]:
    return q("""select m.match_id, m.date, m.league, m.team1, m.team2,
                       pm.bat_n, pm.bat_v, pm.bat_w, pm.bowl_n, pm.bowl_v, pm.bowl_w
                from player_match pm join matches m using (sport, match_id)
                where pm.sport = ? and pm.player_id = ? order by m.date, m.match_id""", [sport, player_id])


def _running_value(log: list[dict], role: str) -> list[dict]:
    """Career runs above average, game by game, thinned to a drawable number of points."""
    total, series = 0.0, []
    for game in log:
        total += game[f"{role}_v"]
        series.append(dict(date=game["date"], value=total))
    step = max(1, len(series) // SERIES_POINTS)
    return series[::step] + series[-1:]


def _splits(sport: str, player_id: str) -> list[dict]:
    return q("""select role, dim, key, sum(n) as n, sum(runs) as runs, sum(outs) as outs,
                       sum(rae) as rae, sum(wpa) as wpa
                from splits where sport = ? and player_id = ?
                group by all order by role, dim, key""", [sport, player_id])


SKILLS = [f"d{number}" for number in range(1, 6)]   # the five skill columns of a profile
MOST_ALIKE = 5


def _most_alike(sport: str, player_id: str, profile: dict | None) -> list[dict]:
    """The players whose five skills sit closest to this one's, in the same role and format.

    `match` is 100 minus the typical gap per skill, in percentile points.
    """
    if profile is None:
        return []
    role, fmt = profile["role"], profile["fmt"]
    mine = q(f"""select {", ".join(SKILLS)} from profiles
                 where sport = ? and player_id = ? and role = ? and fmt = ?""", [sport, player_id, role, fmt])
    if not mine:
        return []
    squares = " + ".join(f"pow({skill} - ?, 2)" for skill in SKILLS)
    rows = q(f"""select player_id, name, fmt, sqrt(({squares}) / {len(SKILLS)}) as gap from profiles
                 where sport = ? and role = ? and fmt = ? and player_id <> ?
                 order by gap, player_id limit {MOST_ALIKE}""",
             [*(mine[0][skill] for skill in SKILLS), sport, role, fmt, player_id])
    return [dict(player_id=row["player_id"], name=row["name"], fmt=row["fmt"],
                 match=max(0.0, 100 - row["gap"])) for row in rows]


def extra(sport: str, player_id: str) -> dict:
    """The parts of a player page beyond the season tables."""
    log = _game_log(sport, player_id)
    role = "bat" if sum(g["bat_n"] for g in log) >= sum(g["bowl_n"] for g in log) else "bowl"
    every = profiles(sport, player_id)
    main = primary(every)
    name = name_of(sport, player_id)
    return dict(
        role=role,
        lede=stories.player_lede(player_id, name, role, spec_for(sport, role), main.get(role)),
        profiles=every,
        profile=main,
        log=log[::-1][:15],
        series=_running_value(log, role),
        splits=_splits(sport, player_id),
        alike=_most_alike(sport, player_id, main.get(role)),
    )
