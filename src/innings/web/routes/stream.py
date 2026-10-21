"""The live stream: matches now flowing through Kafka, pushed to the page as they change."""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from ...stream.board import board

router = APIRouter(prefix="/api/stream")
PUSH_EVERY = 0.25   # seconds between looks at the board
BEAT = 4            # pushes of nothing new before the figures are sent anyway


@router.get("")
def now():
    """The matches in play, with every point of their charts so far."""
    return board.snapshot()


@router.get("/events")
async def events(request: Request, after: int = 0):
    """Server-sent events: each message holds the records since the last one."""
    async def push():
        cursor, quiet = after, 0
        while not await request.is_disconnected():
            news = board.since(cursor)
            quiet = 0 if news.get("records") else quiet + 1
            if news.get("reload") or news.get("records") or quiet >= BEAT:
                yield f"data: {json.dumps(news, separators=(',', ':'))}\n\n"
                quiet = 0
            if news.get("reload"):
                return
            cursor = news["cursor"]
            await asyncio.sleep(PUSH_EVERY)

    # "no-transform" stops the website in front from compressing this. Compression waits to
    # fill a buffer before it sends, which would hold every ball back.
    return StreamingResponse(push(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"})
