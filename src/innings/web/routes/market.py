"""Innings against the betting market (docs/CALIBRATION.md). `innings market` writes the
report; this only reads it and puts it in the shape the page draws."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends

from ...market.compare import REPORT
from ..specs import known_sport

router = APIRouter(prefix="/api/market", dependencies=[Depends(known_sport)])

LABELS = {
    "FIRST_BALL": "First ball",
    "FIRST_INN_FOUR_OV": "1st innings, 4 overs", "FIRST_INN_SIX_OV": "1st innings, 6 overs",
    "FIRST_INN_TEN_OV": "1st innings, 10 overs", "FIRST_INN_FIFTEEN_OV": "1st innings, 15 overs",
    "FIRST_INN_CONCLUSION": "End of 1st innings",
    "SECOND_INN_FOUR_OV": "Chase, 4 overs", "SECOND_INN_SIX_OV": "Chase, 6 overs",
    "SECOND_INN_TEN_OV": "Chase, 10 overs", "SECOND_INN_FIFTEEN_OV": "Chase, 15 overs",
}


def shape(report: dict) -> dict:
    """What the page shows, worked out here so the browser only draws."""
    moments = [{
        "label": LABELS[m["moment"]], "n": m["n"],
        "innings": m["brier_model"], "market": m["brier_market"], "gap": m["brier_gap"],
        "low": m["brier_gap_interval"][0], "high": m["brier_gap_interval"][1],
        "clear": m["brier_gap_interval"][0] > 0 or m["brier_gap_interval"][1] < 0,
        "blend": m.get("brier_blend_blend_rows"),
        "innings_blend_rows": m.get("brier_model_blend_rows"),
        "market_blend_rows": m.get("brier_market_blend_rows"),
    } for m in report["moments"]]
    pooled = report["pooled"]
    calibration = [
        {"model": source, "predicted": b["said"], "actual": b["happened"], "n": b["n"]}
        for source, key in (("innings", "calibration_model"), ("market", "calibration_market"))
        for b in pooled[key]["bins"]
    ]
    widest = max(moments, key=lambda m: m["gap"])
    return {
        "matches": report["matches"],
        "chances": pooled["n"],
        "calibration_error": {"innings": pooled["calibration_model"]["error"],
                              "market": pooled["calibration_market"]["error"],
                              "gap_interval": pooled["calibration_gap_interval"]},
        "calibration": calibration,
        "moments": moments,
        "widest": widest,
        "betting": report["betting"],
    }


@router.get("")
def market(sport: str):
    """The comparison, or null before `innings market` has been run."""
    return shape(json.loads(REPORT.read_text())) if REPORT.exists() else None
