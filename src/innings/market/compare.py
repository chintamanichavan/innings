"""Score the model's chances and the market's on the same matches at the same moments."""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from ..config import DATA
from . import betfair, moments, refit

REPORT = DATA / "market" / "report.json"
BINS = 10
EDGE = 0.05          # back a side when the model's chance beats the price's by this much
RESAMPLES = 2000


# ---- joining the two sources ----

def bbl_matches(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Big Bash matches in the priced seasons, with whether each is clean enough to score."""
    matches = con.execute("""
        select match_id, date, season, team1, team2, winner, result, method, max_balls
        from ck_matches where competition = 'BBL' and gender = 'male'
    """).df()
    matches["date"] = pd.to_datetime(matches["date"]).dt.date
    matches = matches[matches["season"].isin(betfair.SEASONS)]
    matches["clean"] = (matches["result"] == "win") & matches["method"].isna() & (matches["max_balls"] == 120)
    return matches


def join(matches: pd.DataFrame, market: pd.DataFrame) -> pd.DataFrame:
    """Each priced match with its Cricsheet record, matched on the two sides and the date
    (a day either way, since a night match can cross midnight in one source's time zone)."""
    rows = []
    pairs = [frozenset(pair) for pair in zip(matches["team1"], matches["team2"], strict=True)]
    for _, m in market.iterrows():
        same_sides = np.array([pair == {m["side_a"], m["side_b"]} for pair in pairs], dtype=bool)
        near_date = np.array([abs((d - m["date"]).days) <= 1 for d in matches["date"]], dtype=bool)
        found = matches[same_sides & near_date]
        if len(found) == 1:
            rows.append({**m.to_dict(), **found.iloc[0].drop(["date", "season", "winner"]).to_dict(),
                         "cricsheet_winner": found.iloc[0]["winner"]})
    return pd.DataFrame(rows)


# ---- scoring ----

def brier(p: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((p - y) ** 2))


def log_loss(p: np.ndarray, y: np.ndarray) -> float:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def calibration(p: np.ndarray, y: np.ndarray) -> dict:
    """Chances in ten equal bins: each bin's average chance and how often the side won. The
    error is the gap between the two, averaged over all chances.

    Each chance is counted from both sides (p for one side, 1 - p for the other), so the answer
    does not depend on which side a source happens to list first."""
    p, y = np.concatenate([p, 1 - p]), np.concatenate([y, 1 - y])
    bins = np.minimum((p * BINS).astype(int), BINS - 1)
    rows, error = [], 0.0
    for b in range(BINS):
        inside = bins == b
        if inside.any():
            said, happened = float(p[inside].mean()), float(y[inside].mean())
            rows.append({"bin": b, "n": int(inside.sum()), "said": said, "happened": happened})
            error += inside.sum() * abs(said - happened)
    return {"bins": rows, "error": error / len(p)}


def resampled(by_match: pd.DataFrame, statistic, seed: int = 0) -> tuple[float, float]:
    """A 95% interval for `statistic(rows)`, resampling whole matches."""
    rng = np.random.default_rng(seed)
    ids = by_match["match_id"].unique()
    groups = {i: g for i, g in by_match.groupby("match_id")}
    values = []
    for _ in range(RESAMPLES):
        pick = rng.choice(ids, size=len(ids), replace=True)
        values.append(statistic(pd.concat([groups[i] for i in pick], ignore_index=True)))
    low, high = np.percentile(values, [2.5, 97.5])
    return float(low), float(high)


def bets(rows: pd.DataFrame) -> pd.DataFrame:
    """One unit on whichever side the model rates above the market by more than EDGE, at the
    best back price; the return is the profit per unit, before commission."""
    out = []
    for _, r in rows.iterrows():
        for side, p_model, p_market, price in (
                ("a", r["p_model"], r["p_market"], r["back_a"]),
                ("b", 1 - r["p_model"], 1 - r["p_market"], r["back_b"])):
            if p_model - p_market > EDGE and np.isfinite(price) and price > 1:
                won = r["y"] == 1 if side == "a" else r["y"] == 0
                out.append({"match_id": r["match_id"], "moment": r["moment"],
                            "profit": price - 1 if won else -1.0})
    return pd.DataFrame(out, columns=["match_id", "moment", "profit"])


# ---- the whole study ----

def chances(con: duckdb.DuckDBPyConnection, joined: pd.DataFrame) -> pd.DataFrame:
    """One row per match and moment: the model's chance and the market's, for side A, and
    whether side A won."""
    starts = {s: min(joined.loc[joined["season"] == s, "date"]) for s in joined["season"].unique()}
    ids = {s: joined.loc[joined["season"] == s, "match_id"].tolist() for s in starts}

    first = refit.pre_match(con, starts, ids).merge(joined, on="match_id")
    first["p_pre"] = np.where(first["team1"] == first["side_a"], first["p_first"], 1 - first["p_first"])
    rows = [pd.DataFrame({
        "match_id": first["match_id"], "season": first["season"], "moment": "FIRST_BALL",
        "p_model": np.where(first["team1"] == first["side_a"], first["p_first"], 1 - first["p_first"]),
        "p_market": first["FIRST_BALL"], "back_a": first["FIRST_BALL_back_a"],
        "back_b": first["FIRST_BALL_back_b"], "side_a": first["side_a"]})]

    balls = refit.t20_balls(con)
    states = moments.states(balls[balls["match_id"].isin(joined["match_id"])])
    states = states.merge(joined[["match_id", "season", "side_a"]], on="match_id")
    for season, start in starts.items():
        these = states[states["season"] == season].reset_index(drop=True)
        batting = refit.in_play(balls, these, start)
        p_a = np.where(these["bat_team"] == these["side_a"], batting, 1 - batting)
        prices = joined.set_index("match_id").loc[these["match_id"]]
        rows.append(pd.DataFrame({
            "match_id": these["match_id"], "season": season, "moment": these["moment"],
            "p_model": p_a, "side_a": these["side_a"],
            "p_market": [prices.iloc[i][m] for i, m in enumerate(these["moment"])],
            "back_a": [prices.iloc[i][f"{m}_back_a"] for i, m in enumerate(these["moment"])],
            "back_b": [prices.iloc[i][f"{m}_back_b"] for i, m in enumerate(these["moment"])]}))
    out = pd.concat(rows, ignore_index=True)
    out["p_pre"] = first.set_index("match_id")["p_pre"].loc[out["match_id"]].to_numpy()
    winners = joined.set_index("match_id")["cricsheet_winner"]
    out["y"] = (winners.loc[out["match_id"]].to_numpy() == out["side_a"].to_numpy()).astype(int)
    out = out.dropna(subset=["p_market"]).reset_index(drop=True)
    out["p_blend"] = blend(out)
    return out


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def blend(rows: pd.DataFrame) -> np.ndarray:
    """The in-play chance with the pre-match forecast mixed back in: what the model would say
    if it remembered who is playing. The two weights for each innings are fitted on earlier
    seasons' rows only, so the first season gets no blend (missing)."""
    from sklearn.linear_model import LogisticRegression

    out = np.full(len(rows), np.nan)
    chasing = rows["moment"].str.startswith("SECOND") | (rows["moment"] == "FIRST_INN_CONCLUSION")
    innings = np.where(chasing, 2, 1)
    inputs = np.column_stack([_logit(rows["p_model"].to_numpy()), _logit(rows["p_pre"].to_numpy())])
    seasons = sorted(rows["season"].unique())
    for i, season in enumerate(seasons[1:], start=1):
        for half in (1, 2):
            in_play = (innings == half) & (rows["moment"] != "FIRST_BALL").to_numpy()
            earlier = rows["season"].isin(seasons[:i]).to_numpy() & in_play
            these = (rows["season"] == season).to_numpy() & in_play
            if earlier.any() and these.any():
                model = LogisticRegression(C=1.0).fit(inputs[earlier], rows["y"].to_numpy()[earlier])
                out[these] = model.predict_proba(inputs[these])[:, 1]
    return out


def score(rows: pd.DataFrame) -> dict:
    """Everything the page shows."""
    by_moment = []
    for moment in betfair.MOMENTS:
        these = rows[rows["moment"] == moment]
        if these.empty:
            continue
        p, q, y = these["p_model"].to_numpy(), these["p_market"].to_numpy(), these["y"].to_numpy()
        gap = resampled(these, lambda r: brier(r["p_model"].to_numpy(), r["y"].to_numpy())
                        - brier(r["p_market"].to_numpy(), r["y"].to_numpy()))
        blended = these.dropna(subset=["p_blend"])
        blend_scores = {"n_blend": len(blended)}
        if len(blended):   # the same rows for all three, so the three numbers compare
            for name in ("blend", "model", "market"):
                blend_scores[f"brier_{name}_blend_rows"] = brier(blended[f"p_{name}"].to_numpy(),
                                                                 blended["y"].to_numpy())
        by_moment.append({"moment": moment, "n": len(these), **blend_scores,
                          "brier_model": brier(p, y), "brier_market": brier(q, y),
                          "log_loss_model": log_loss(p, y), "log_loss_market": log_loss(q, y),
                          "brier_gap": brier(p, y) - brier(q, y), "brier_gap_interval": gap})
    p, q, y = rows["p_model"].to_numpy(), rows["p_market"].to_numpy(), rows["y"].to_numpy()
    placed = bets(rows)

    def stake_return(placed_bets: pd.DataFrame) -> float:
        return float(placed_bets["profit"].mean()) if len(placed_bets) else 0.0

    return {
        "moments": by_moment,
        "pooled": {"n": len(rows), "brier_model": brier(p, y), "brier_market": brier(q, y),
                   "calibration_model": calibration(p, y), "calibration_market": calibration(q, y),
                   "calibration_gap_interval": resampled(
                       rows, lambda r: calibration(r["p_model"].to_numpy(), r["y"].to_numpy())["error"]
                       - calibration(r["p_market"].to_numpy(), r["y"].to_numpy())["error"])},
        "betting": {"edge": EDGE, "bets": len(placed), "return_per_unit": stake_return(placed),
                    "interval": resampled(placed, stake_return) if len(placed) else [0.0, 0.0]},
    }


def run(con: duckdb.DuckDBPyConnection, report: Path = REPORT) -> dict:
    betfair.download()
    market = betfair.prices()
    matches = bbl_matches(con)
    joined = join(matches, market)
    clean = joined[joined["clean"]]
    rows = chances(con, clean)
    result = {
        "matches": {"in_innings": len(matches), "priced": len(market), "joined": len(joined),
                    "scored": int(clean["match_id"].nunique()),
                    "left_out": {"rain_or_no_result": int((~joined["clean"]).sum()),
                                 "not_found": len(market) - len(joined)}},
        **score(rows),
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=1, default=float))
    return result
