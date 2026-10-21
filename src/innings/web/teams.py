"""Team ratings, and the chance one team beats another."""
from __future__ import annotations

from ..models.predict import win_prob
from .db import per_database, q

# Elo points the home side is worth. Cricket's rating pools have no fixed home side.
HOME_EDGE = {"ck": 0}


def states(sport: str, pool: str) -> list[dict]:
    """Every team's rating today."""
    return q("""select team, elo, form, bat, bowl, games, last_date
                from team_state where sport = ? and pool = ?""", [sport, pool])


def active(sport: str, pool: str, years: int = 2) -> list[dict]:
    """Teams that have played in the last few years, strongest first."""
    rows = states(sport, pool)
    if not rows:
        return []
    newest = max(int(str(r["last_date"])[:4]) for r in rows)
    recent = [r for r in rows if int(str(r["last_date"])[:4]) >= newest - years]
    return sorted(recent, key=lambda r: -r["elo"])


@per_database()
def coefficients(sport: str) -> dict[str, tuple[float, float, float]]:
    rows = q("select feature, coef, mean, scale from pred_model where sport = ?", [sport])
    return {r["feature"]: (r["coef"], r["mean"], r["scale"]) for r in rows}


def chance_first(sport: str, first: dict, second: dict) -> float:
    """Chance that `first` wins. `first` bats first."""
    return win_prob(coefficients(sport), dict(
        elo_diff=first["elo"] - second["elo"] - HOME_EDGE[sport],
        form_diff=first["form"] - second["form"],
        bat_diff=first["bat"] - second["bat"],
        bowl_diff=first["bowl"] - second["bowl"],
    ))
