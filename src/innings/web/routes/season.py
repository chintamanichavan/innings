"""The season played many times over: the running tally, and the report once the job is done.

The job itself runs elsewhere, on a machine with a graphics card. It leaves two small files,
and this only reads them.
"""
from __future__ import annotations

import json

from fastapi import APIRouter

from ...config import SEASON

router = APIRouter(prefix="/api/season")


def _read(name: str) -> dict | None:
    path = SEASON / name
    return json.loads(path.read_text()) if path.exists() else None


@router.get("")
def season():
    """`tally` is rewritten every second while the job runs. `report` appears when it ends."""
    return {"tally": _read("tally.json"), "report": _read("report.json")}
