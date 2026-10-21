"""Betfair Exchange prices for the Big Bash League, as Betfair's data scientists publish them.

Each file has one row per side per match, with the best back and lay price at eleven moments.
The files are downloaded as they are and never republished; only the comparison is shown.
"""
from __future__ import annotations

import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import RAW

SOURCE = "https://betfair-datascientists.github.io/data/assets/{name}_Match_Odds.csv"
FOLDER = RAW / "betfair"
SEASONS = {"2020/21": "BBL10", "2021/22": "BBL11", "2022/23": "BBL12",
           "2023/24": "BBL13", "2024/25": "BBL14", "2025/26": "BBL15"}

# The moments the files price, in match order, by the name used in their columns.
MOMENTS = ["FIRST_BALL",
           "FIRST_INN_FOUR_OV", "FIRST_INN_SIX_OV", "FIRST_INN_TEN_OV", "FIRST_INN_FIFTEEN_OV",
           "FIRST_INN_CONCLUSION",
           "SECOND_INN_FOUR_OV", "SECOND_INN_SIX_OV", "SECOND_INN_TEN_OV", "SECOND_INN_FIFTEEN_OV"]

WIDEST_SPREAD = 0.2   # a price whose back and lay differ by more than this share of it is not used


def download(folder: Path = FOLDER) -> None:
    """Fetch any season not already on disk."""
    folder.mkdir(parents=True, exist_ok=True)
    for name in SEASONS.values():
        path = folder / f"{name}_Match_Odds.csv"
        if not path.exists():
            urllib.request.urlretrieve(SOURCE.format(name=name), path)


def chance(back: pd.Series, lay: pd.Series) -> pd.Series:
    """One side's chance from its prices: the middle of 1/back and 1/lay.

    Missing when either price is missing or the two are too far apart to mean much.
    """
    usable = back.notna() & lay.notna() & ((back - lay).abs() <= WIDEST_SPREAD * np.minimum(back, lay))
    return ((1 / back + 1 / lay) / 2).where(usable)


def prices(folder: Path = FOLDER) -> pd.DataFrame:
    """One row per match: date, the two sides, the winner, and side A's chance at each moment.

    Side A is the side Betfair lists first. The two sides' chances are scaled to add to one;
    a moment where either side's price is unusable is missing.
    """
    matches = []
    for season, name in SEASONS.items():
        rows = pd.read_csv(folder / f"{name}_Match_Odds.csv")
        for _, sides in rows.groupby("MARKET_ID", sort=False):
            if len(sides) != 2:
                continue
            a, b = sides.iloc[0], sides.iloc[1]
            match = {"season": season, "date": pd.Timestamp(a["EVENT_DATE"][:10]).date(),
                     "side_a": a["RUNNER_NAME"], "side_b": b["RUNNER_NAME"],
                     "winner": a["RUNNER_NAME"] if a["IS_WINNER"] == 1 else
                               b["RUNNER_NAME"] if b["IS_WINNER"] == 1 else None}
            for moment in MOMENTS:
                pa = chance(sides[f"BEST_BACK_{moment}"], sides[f"BEST_LAY_{moment}"])
                total = pa.sum(min_count=2)
                match[moment] = float(pa.iloc[0] / total) if pd.notna(total) else np.nan
                match[f"{moment}_back_a"] = float(a[f"BEST_BACK_{moment}"])
                match[f"{moment}_back_b"] = float(b[f"BEST_BACK_{moment}"])
            matches.append(match)
    return pd.DataFrame(matches)
