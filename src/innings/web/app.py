"""The API server: data and models as JSON under /api. The website is in frontend/."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from ..stream import board
from .routes import feed, forecasts, games, lab, market, news, season, stats, stream, teams


@asynccontextmanager
async def lifespan(_: FastAPI):
    board.start()   # begin following the live stream, if a Kafka broker has been named
    yield


app = FastAPI(title="Innings", lifespan=lifespan)
for module in (stats, teams, feed, games, forecasts, market, lab, news, stream, season):
    app.include_router(module.router)
