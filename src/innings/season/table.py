"""The league table of many simulated seasons at once, and who reaches the playoffs."""
from __future__ import annotations

import numpy as np

FULL_INNINGS = 120


def top_four(sides: np.ndarray, winner: np.ndarray, runs: np.ndarray, balls: np.ndarray,
             teams: int, random: np.random.Generator) -> np.ndarray:
    """The first four teams of each season's table, best first. Returns [seasons, 4] team numbers.

    sides    [matches, 2]           the two teams of each league match
    winner   [seasons, matches]     which side won: 0 or 1
    runs     [seasons, matches, 2]  each side's runs
    balls    [seasons, matches, 2]  balls each side faced; a side bowled out counts as the full 120

    Two points for a win. Level on points, the better net run rate goes ahead, as in the IPL.
    """
    is_team = np.eye(teams)[sides]                                   # [matches, 2, teams]
    won = np.eye(2)[winner]                                          # [seasons, matches, 2]

    def per_team(by_side: np.ndarray) -> np.ndarray:
        return np.einsum("smk,mkt->st", by_side, is_team)

    points = 2 * per_team(won)
    run_rate_for = per_team(runs) / per_team(balls)
    run_rate_against = per_team(runs[:, :, ::-1]) / per_team(balls[:, :, ::-1])
    net_run_rate = 6 * (run_rate_for - run_rate_against)             # runs an over; always well inside +-20
    coin = random.random(points.shape) * 1e-6                        # settles what little is still level
    return np.argsort(-(points + net_run_rate / 100 + coin), axis=1)[:, :4]
