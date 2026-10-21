"""The Lab: the neural network's report card, its map of players, and what it can do live."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ...nn import serve
from ...nn.features import BALLS_SCALE
from .. import lab

router = APIRouter(prefix="/api/lab")


def _require_model() -> None:
    if not serve.available():
        raise HTTPException(503, "The neural network has not been trained yet. Run `innings train`.")


@router.get("")
def report():
    """How the network was trained and how it scored."""
    _require_model()
    return {**lab.card(), "win_models": lab.win_model_scores()}


@router.get("/players")
def player_map():
    """Where the network places each well-known batter, epoch by epoch."""
    _require_model()
    return lab.players()


@router.get("/matchup")
def matchup(batter: str, bowler: str, fmt: str = "T20", phase: str = "middle", league: str = ""):
    _require_model()
    if fmt not in lab.PHASES or phase not in lab.PHASES[fmt]:
        raise HTTPException(400, "unknown format or phase")
    return lab.matchup(batter, bowler, fmt, phase, league)


@router.get("/simulate")
def simulate(fmt: str = "T20", league: str = "", balls: int = 0, wickets: int = 0, score: int = 0,
             target: int | None = None, striker: str = "", bowler: str = "", seed: int = 0):
    _require_model()
    if fmt not in serve.LIMITED:
        raise HTTPException(400, "only T20 and ODI innings can be simulated")
    if balls >= BALLS_SCALE[fmt]:
        raise HTTPException(400, "the innings is already over")
    return lab.simulate(fmt, league, balls, wickets, score, target, striker, bowler, seed)
