"""Team one's chance of winning in each of many matches, asked of the saved models at once.

Asking the models about 500 states together costs little more than asking about one, so the
scorer hands over every ball it has just read in one go.
"""
from __future__ import annotations

import pandas as pd

from ..models import cricket_limited
from .state import MatchState

_loaded: dict[str, tuple[int, cricket_limited.Saved]] = {}


def _models(fmt: str) -> cricket_limited.Saved:
    """One format's models, read again whenever a rebuild has written new ones."""
    written = (cricket_limited.MODEL_FOLDER / f"{fmt}.joblib").stat().st_mtime_ns
    if fmt not in _loaded or _loaded[fmt][0] != written:
        _loaded[fmt] = (written, cricket_limited.load(fmt))
    return _loaded[fmt][1]


def team1_chances(states: list[MatchState]) -> list[float]:
    """Team one's chance in each state: the real result if the match is decided, else the model's."""
    chances = [state.result for state in states]
    for fmt in {state.fmt for state in states}:
        models = _models(fmt)
        open_matches = [at for at, state in enumerate(states) if state.fmt == fmt and state.result is None]
        if not open_matches:
            continue
        rows = pd.DataFrame([states[at].before_next_ball() for at in open_matches])
        code_of = {name: code for code, name in enumerate(models.competitions)}
        rows["comp_code"] = [code_of[states[at].competition] for at in open_matches]
        for at, batting in zip(open_matches, models.win_chance(rows), strict=True):
            chances[at] = float(batting if states[at].innings == 1 else 1 - batting)
    return chances
