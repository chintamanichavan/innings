"""The Lab: what the neural network learned, and two things it can do on request."""
from __future__ import annotations

import json
from functools import lru_cache

import numpy as np

from ..nn import serve
from ..nn.features import BALLS_SCALE, OUTCOME_RUNS, OUTCOMES, WICKET
from ..nn.serve import Scenario
from .db import q

# A typical moment in each phase of an innings, to ask the network about a matchup:
# (balls bowled, wickets down, score).
PHASES = {
    "T20": {"start": (12, 0, 15), "middle": (60, 2, 78), "end": (108, 4, 152)},
    "ODI": {"start": (30, 0, 26), "middle": (150, 2, 128), "end": (270, 5, 245)},
    "Test": {"start": (30, 0, 15), "middle": (300, 3, 165), "end": (540, 6, 300)},
}
DEFAULT_LEAGUE = {"T20": "IPL", "ODI": "ODI", "Test": "Test"}
SHOWN_PATHS = 150        # simulated innings drawn on the page
COUNTED_PATHS = 1000     # simulated innings behind the numbers
PLOTTED_POINTS = 30      # points drawn along each innings: enough for the eye, small to send


@lru_cache(maxsize=1)
def card() -> dict:
    return json.loads((serve.FOLDER / "card.json").read_text())


@lru_cache(maxsize=1)
def players() -> dict:
    return json.loads((serve.FOLDER / "players.json").read_text())


def win_model_scores() -> dict[str, float]:
    """The Brier score of each win model the site already uses, to set beside the network's."""
    rows = q("select model, value from model_metrics where sport = 'ck' and metric = 'brier'")
    return {row["model"]: row["value"] for row in rows}


def _name(player_id: str) -> str | None:
    rows = q("select name from players where sport = 'ck' and player_id = ?", [player_id])
    return rows[0]["name"] if rows else None


def _summary(chances: np.ndarray) -> dict:
    return dict(
        chances=[float(chance) for chance in chances],
        runs_per_ball=float((chances * OUTCOME_RUNS).sum()),
        wicket=float(chances[WICKET]),
        boundary=float(chances[OUTCOMES.index("4")] + chances[OUTCOMES.index("6")]),
    )


def matchup(batter: str, bowler: str, fmt: str, phase: str, league: str = "") -> dict:
    """What the network expects on one ball between this batter and this bowler, beside
    what it expects from two players it knows nothing about in the same spot."""
    net = serve.network()
    balls, wickets, score = PHASES[fmt][phase]
    spot = dict(fmt=fmt, league=league or DEFAULT_LEAGUE[fmt], balls_bowled=balls, wickets=wickets,
                score=score, striker_runs=12, striker_balls=10)
    batter_id, bowler_id = net.id_of("batters", batter), net.id_of("bowlers", bowler)
    pair = serve.next_ball(net, Scenario(**spot, striker=batter_id, bowler=bowler_id))
    average = serve.next_ball(net, Scenario(**spot))
    return dict(
        outcomes=OUTCOMES, fmt=fmt, phase=phase, league=spot["league"],
        batter=dict(id=batter, name=_name(batter), known=batter_id != 0),
        bowler=dict(id=bowler, name=_name(bowler), known=bowler_id != 0),
        pair=_summary(pair), average=_summary(average),
    )


def _histogram(scores: np.ndarray, bins: int = 24) -> list[dict]:
    counts, edges = np.histogram(scores, bins=bins)
    return [dict(low=float(edges[i]), high=float(edges[i + 1]), share=float(counts[i] / len(scores)))
            for i in range(bins)]


def _path(scores: np.ndarray, start: Scenario, every: int) -> list[list[int]]:
    """One simulated innings as [ball, score] points for the drawing: the start, then every
    few balls, then the ball it ended on. `scores` holds the score after each ball, or -1
    for balls the innings never reached."""
    last_ball = int(np.where(scores >= 0)[0][-1])
    later = dict.fromkeys([*range(start.balls_bowled + every, last_ball, every), last_ball])
    # The start is given, not read: a wide before the next legal ball would already be in `scores`.
    return [[start.balls_bowled, start.score], *([ball, int(scores[ball])] for ball in later)]


def simulate(fmt: str, league: str, balls: int, wickets: int, score: int, target: int | None,
             striker: str, bowler: str, seed: int) -> dict:
    """Let the network play out the rest of an innings many times."""
    net = serve.network()
    limit = int(BALLS_SCALE[fmt])
    scenario = Scenario(
        fmt=fmt, league=league or DEFAULT_LEAGUE[fmt], balls_bowled=min(max(balls, 0), limit - 1),
        wickets=min(max(wickets, 0), 9), score=max(score, 0), target=target,
        striker=net.id_of("batters", striker), bowler=net.id_of("bowlers", bowler),
    )
    result = serve.simulate(net, scenario, runs=COUNTED_PATHS, seed=seed)
    totals = result["score"]
    drawn = result["by_ball"][:SHOWN_PATHS]
    every = max(1, (limit - scenario.balls_bowled) // PLOTTED_POINTS)
    paths = [_path(scores, scenario, every) for scores in drawn]
    return dict(
        fmt=fmt, start=dict(balls=scenario.balls_bowled, wickets=scenario.wickets, score=scenario.score),
        target=target, limit=limit, paths=paths, innings=COUNTED_PATHS, mean=float(totals.mean()),
        low=float(np.percentile(totals, 10)), high=float(np.percentile(totals, 90)),
        histogram=_histogram(totals),
        win=float(result["reached"].mean()) if target is not None else None,
        all_out=float((result["wickets"] >= 10).mean()),
    )
