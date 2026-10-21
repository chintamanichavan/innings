"""The forecaster's public record."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import forecasts
from ..specs import known_sport

router = APIRouter(prefix="/api/forecasts", dependencies=[Depends(known_sport)])


@router.get("")
def record(sport: str):
    calls = forecasts.calls(sport)
    known = [call for call in calls if call["major"]]
    return dict(
        record=forecasts.tally(calls),
        by_league=forecasts.tally_by(calls, "league"),
        by_year=forecasts.tally_by(calls, "year"),
        series=forecasts.running_total(calls),
        recent=known[::-1][:30],
        misses=forecasts.worst_misses(known),
    )
