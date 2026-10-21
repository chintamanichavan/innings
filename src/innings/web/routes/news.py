"""Headlines and live scores from publishers' free feeds."""
from __future__ import annotations

from fastapi import APIRouter

from ... import feeds
from ...config import FULL_MEMBERS

router = APIRouter(prefix="/api")
MAX_HEADLINES = 150


@router.get("/news")
def news(limit: int = 60, source: str = ""):
    return feeds.news(min(max(limit, 1), MAX_HEADLINES), source)


def _national(team: str) -> str:
    return team.removesuffix(" Women")


@router.get("/livescores")
def live_scores():
    """Live matches: those under way first, and among them the leading nations first."""
    scores = feeds.live()

    def rank(match: dict) -> tuple:
        leading = sum(_national(match[side]["team"]) in FULL_MEMBERS for side in ("first", "second"))
        return (not match["started"], -leading)

    scores["matches"].sort(key=rank)
    return scores
