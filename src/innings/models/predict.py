"""Forecasting a match before it starts.

One pass through history, oldest match first, gives every match the ratings as they stood
beforehand: Elo, recent form, and the strength of the named lineups. A small logistic model
blends those four differences into a chance. It is scored only on years it never trained on.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field

import duckdb
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .common import classifier_scores, write_table
from .ratings import PARAMS, PlayerRatings, TeamRatings

# Each is the first-named side's value minus the second's. The first-named side bats first.
FEATURES = ["elo_diff", "form_diff", "bat_diff", "bowl_diff"]
TEST_YEARS = 4                  # the most recent years, each forecast from the years before it

TEAM_STATE_COLUMNS = ["sport", "pool", "team", "elo", "form", "bat", "bowl", "games", "last_date"]
MODEL_COLUMNS = ["sport", "feature", "coef", "mean", "scale"]
ELO_HISTORY_COLUMNS = ["sport", "pool", "team", "date", "elo"]


@dataclass
class History:
    """Everything one pass through a sport's matches produces."""
    features: pd.DataFrame                       # one row per match: match_id and FEATURES
    teams: TeamRatings
    players: PlayerRatings
    last_seen: dict = field(default_factory=dict)      # (pool, team) -> {date, lineup}
    elo_after: list = field(default_factory=list)      # (pool, team, date, elo) after each result


# ---- loading ----

def _load_matches(con: duckdb.DuckDBPyConnection, sport: str) -> pd.DataFrame:
    matches = con.execute("select * from matches where sport = ? order by date, match_id", [sport]).df()
    matches["date"] = pd.to_datetime(matches["date"]).dt.date
    return matches


def _load_lineups(con: duckdb.DuckDBPyConnection, sport: str) -> dict:
    """match_id -> team -> [player_id]."""
    lineups: dict = defaultdict(lambda: defaultdict(list))
    rows = con.execute("select match_id, team, player_id from lineups where sport = ?", [sport]).fetchall()
    for match_id, team, player_id in rows:
        lineups[match_id][team].append(player_id)
    return lineups


def _load_player_values(con: duckdb.DuckDBPyConnection, sport: str) -> dict:
    """match_id -> [(player_id, bat chances, bat value, bowl chances, bowl value)]."""
    values: dict = defaultdict(list)
    rows = con.execute("""select match_id, player_id, bat_n, bat_v, bowl_n, bowl_v from player_match
                          where sport = ?""", [sport]).fetchall()
    for match_id, *line in rows:
        values[match_id].append(tuple(line))
    return values


# ---- one pass through history ----

def walk(sport: str, matches: pd.DataFrame, lineups: dict, player_values: dict) -> History:
    """Give each match the ratings from before it, then update them with what happened."""
    params = PARAMS[sport]
    teams, players = TeamRatings(params), PlayerRatings(params)
    history = History(features=pd.DataFrame(), teams=teams, players=players)
    rows = []
    for match in matches.itertuples(index=False):
        day = match.date.toordinal()
        first, second = (match.pool, match.team1), (match.pool, match.team2)
        teams.start_of_match(first, match.year)
        teams.start_of_match(second, match.year)

        # A player is rated inside one format, so the rating key carries it.
        named = {team: [(player, match.fmt) for player in lineup]
                 for team, lineup in lineups.get(match.match_id, {}).items()}
        first_bat, first_bowl = players.lineup_strength(named.get(match.team1, []), day)
        second_bat, second_bowl = players.lineup_strength(named.get(match.team2, []), day)
        rows.append((
            match.match_id,
            teams.elo[first] - teams.elo[second] - params.home_edge,
            teams.form(first) - teams.form(second),
            first_bat - second_bat,
            first_bowl - second_bowl,
        ))
        history.last_seen[first] = dict(date=match.date, lineup=named.get(match.team1, []))
        history.last_seen[second] = dict(date=match.date, lineup=named.get(match.team2, []))

        if isinstance(match.winner, str):   # a draw or no-result moves no ratings
            teams.record(first, second, 1.0 if match.winner == match.team1 else 0.0)
            history.elo_after.append((match.pool, match.team1, match.date, teams.elo[first]))
            history.elo_after.append((match.pool, match.team2, match.date, teams.elo[second]))
        for player, *line in player_values.get(match.match_id, []):
            players.add((player, match.fmt), day, *line)

    history.features = pd.DataFrame(rows, columns=["match_id", *FEATURES])
    return history


# ---- the model ----

def _new_model():
    return make_pipeline(StandardScaler(), LogisticRegression(C=1.0))


def _decided_matches(matches: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    """Matches with a winner, their features, and `y`: 1 when the first-named side won."""
    decided = matches.merge(features, on="match_id")
    decided = decided[decided["winner"].notna()].copy()
    decided["y"] = (decided["winner"] == decided["team1"]).astype(int)
    # The first year only warms the ratings up; its forecasts would be made blind.
    return decided[decided["year"] > decided["year"].min()]


def _test_year_by_year(sport: str, decided: pd.DataFrame) -> tuple[list[dict], list[pd.DataFrame]]:
    """Forecast each recent year from the years before it. Returns scores and the forecasts."""
    scores, forecasts = [], []
    for year in sorted(decided["year"].unique())[-TEST_YEARS:]:
        past, this_year = decided[decided["year"] < year], decided[decided["year"] == year]
        always_usual_side = np.full(len(this_year), past["y"].mean())
        elo_only = (_new_model().fit(past[["elo_diff"]], past["y"])
                    .predict_proba(this_year[["elo_diff"]])[:, 1])
        full = _new_model().fit(past[FEATURES], past["y"]).predict_proba(this_year[FEATURES])[:, 1]
        for name, chances in (("base rate", always_usual_side), ("elo", elo_only), ("full", full)):
            scores.append({"sport": sport, "year": int(year), "model": name,
                           **classifier_scores(this_year["y"], chances)})
        forecasts.append(pd.DataFrame({
            "sport": sport, "match_id": this_year["match_id"].to_numpy(), "year": int(year),
            "p_elo": elo_only, "p_full": full, "y": this_year["y"].to_numpy(),
        }))
    return scores, forecasts


def _fit_final(sport: str, decided: pd.DataFrame) -> list[tuple]:
    """Fit on everything and return the model as rows: (sport, feature, coef, mean, scale)."""
    model = _new_model().fit(decided[FEATURES], decided["y"])
    scaler, logistic = model.named_steps["standardscaler"], model.named_steps["logisticregression"]
    rows = [(sport, "intercept", float(logistic.intercept_[0]), 0.0, 1.0)]
    for feature, coef, mean, scale in zip(FEATURES, logistic.coef_[0], scaler.mean_, scaler.scale_,
                                          strict=True):
        rows.append((sport, feature, float(coef), float(mean), float(scale)))
    return rows


def win_prob(coefs: dict[str, tuple[float, float, float]], diffs: dict[str, float]) -> float:
    """The fitted model, applied by hand. `coefs` maps a feature to (coef, mean, scale).

    Returns the chance that the first-named side wins. It bats first.
    """
    score = coefs["intercept"][0]
    for feature in FEATURES:
        coef, mean, scale = coefs[feature]
        score += coef * (diffs[feature] - mean) / scale
    return 1 / (1 + math.exp(-score))


# ---- where every team stands today ----

def _games_played(matches: pd.DataFrame) -> pd.Series:
    """(pool, team) -> number of matches."""
    pools = pd.concat([matches["pool"], matches["pool"]])
    teams = pd.concat([matches["team1"], matches["team2"]])
    return teams.groupby([pools, teams]).size()


def _team_states(sport: str, matches: pd.DataFrame, history: History) -> list[tuple]:
    """Today's rating for every team."""
    today = matches["date"].max().toordinal()
    games = _games_played(matches)
    states = []
    for (pool, team), seen in history.last_seen.items():
        bat, bowl = history.players.lineup_strength(seen["lineup"], today)
        states.append((sport, pool, team, float(history.teams.elo[(pool, team)]),
                       history.teams.form((pool, team)), float(bat), float(bowl),
                       int(games.get((pool, team), 0)), seen["date"]))
    return states


def build(con: duckdb.DuckDBPyConnection) -> None:
    """Write pred_eval, predictions, pred_model, team_state and elo_history."""
    scores, forecasts, model_rows, states, elo_history = [], [], [], [], []
    for sport in PARAMS:
        matches = _load_matches(con, sport)
        history = walk(sport, matches, _load_lineups(con, sport), _load_player_values(con, sport))
        decided = _decided_matches(matches, history.features)

        sport_scores, sport_forecasts = _test_year_by_year(sport, decided)
        scores += sport_scores
        forecasts += sport_forecasts
        model_rows += _fit_final(sport, decided)
        states += _team_states(sport, matches, history)
        elo_history += [(sport, *row) for row in history.elo_after]

    write_table(con, "pred_eval", pd.DataFrame(scores))
    write_table(con, "predictions", pd.concat(forecasts, ignore_index=True))
    write_table(con, "pred_model", pd.DataFrame(model_rows, columns=MODEL_COLUMNS))
    write_table(con, "team_state", pd.DataFrame(states, columns=TEAM_STATE_COLUMNS))
    write_table(con, "elo_history", pd.DataFrame(elo_history, columns=ELO_HISTORY_COLUMNS))
