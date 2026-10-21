"""Every ball in the database as arrays the network can read, split by time.

The split is by year, never at random. A model that will be asked about next season has to
be tested on seasons it has not seen: balls from one match are alike, so a random split
would let it peek.
"""
from __future__ import annotations

from dataclasses import dataclass

import duckdb
import numpy as np
import pandas as pd

from .features import FORMATS, HISTORY, NO_BALL, PAD, RUNS_TO_OUTCOME, UNKNOWN, WICKET, WIDE, numeric_matrix

TRAIN_THROUGH = 2023      # training sees every ball up to the end of this year
VALIDATE_YEAR = 2024      # used to pick the best epoch; never to report a result
MIN_BALLS = 200           # a player or ground needs this many training balls to get its own vector

BALLS_SQL = """
    select e.match_id, e.seq, e.innings, e."over", m.year, m.format as fmt, m.venue,
           m.competition || case when m.gender = 'female' then ' (W)' else '' end as league,
           (m.gender = 'female')::int as women,
           e.batter_id, e.bowler_id, e.bat_team, m.winner,
           e.runs, e.runs_bat, e.wide, e.noball, e.outs,
           e.score_pre, e.wkts_pre, e.inn_balls_pre, e.match_balls_pre, e.lead_pre, e.target
    from ck_events e join ck_matches m using (match_id)
    order by e.match_id, e.seq
"""


@dataclass
class Vocabulary:
    """The ids the network knows. Anything else shares the UNKNOWN id."""
    batters: dict[str, int]
    bowlers: dict[str, int]
    venues: dict[str, int]
    leagues: dict[str, int]

    def sizes(self) -> dict[str, int]:
        return {name: len(ids) + 1 for name, ids in vars(self).items()}   # +1 for UNKNOWN


@dataclass
class Balls:
    """One array per input, all the same length, one row per ball."""
    numeric: np.ndarray      # float32 [n, len(NUMERIC)]
    history: np.ndarray      # int64   [n, HISTORY]   the earlier balls of the innings, newest last
    batter: np.ndarray       # int64   [n]
    bowler: np.ndarray
    venue: np.ndarray
    league: np.ndarray
    fmt: np.ndarray
    outcome: np.ndarray      # int64 [n]  what happened: an index into OUTCOMES
    result: np.ndarray       # int64 [n]  how the match ended for the batting side: index into RESULTS
    year: np.ndarray
    match: np.ndarray        # int64 [n]  a number per match, to group balls

    def __len__(self) -> int:
        return len(self.outcome)

    def where(self, mask: np.ndarray) -> Balls:
        return Balls(**{name: array[mask] for name, array in vars(self).items()})


def load_frame(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return con.execute(BALLS_SQL).df()


def outcome_of(frame: pd.DataFrame) -> np.ndarray:
    """What happened on each ball. A wicket outranks a wide, which outranks the runs."""
    outcome = frame["runs_bat"].clip(upper=7).map(RUNS_TO_OUTCOME).to_numpy()
    outcome = np.where(frame["noball"], NO_BALL, outcome)
    outcome = np.where(frame["wide"], WIDE, outcome)
    return np.where(frame["outs"] > 0, WICKET, outcome).astype(np.int64)


def history_of(outcome: np.ndarray, innings_key: np.ndarray) -> np.ndarray:
    """For each ball, the HISTORY balls before it in the same innings, oldest first."""
    history = np.full((len(outcome), HISTORY), PAD, dtype=np.int64)
    for back in range(1, HISTORY + 1):
        same_innings = innings_key[back:] == innings_key[:-back]
        history[back:, HISTORY - back] = np.where(same_innings, outcome[:-back], PAD)
    return history


def _so_far(values: pd.Series, groups: list) -> np.ndarray:
    """A running total within each group, not counting the current row."""
    return (values.groupby(groups).cumsum() - values).to_numpy()


def numeric_of(frame: pd.DataFrame) -> np.ndarray:
    """The numeric inputs for every ball in the frame."""
    legal = ~(frame["wide"] | frame["noball"])
    faced = (~frame["wide"]).astype(int)
    in_innings = [frame["match_id"], frame["innings"]]
    return numeric_matrix(
        fmt=frame["fmt"].to_numpy(),
        innings=frame["innings"].to_numpy(),
        balls_bowled=frame["inn_balls_pre"].to_numpy(),
        wickets=frame["wkts_pre"].to_numpy(),
        score=frame["score_pre"].to_numpy(),
        target=frame["target"].to_numpy(dtype=float, na_value=np.nan),
        lead=frame["lead_pre"].to_numpy(),
        match_balls=frame["match_balls_pre"].to_numpy(),
        year=frame["year"].to_numpy(),
        women=frame["women"].to_numpy(),
        batter_runs=_so_far(frame["runs_bat"], [*in_innings, frame["batter_id"]]),
        batter_balls=_so_far(faced, [*in_innings, frame["batter_id"]]),
        bowler_balls=_so_far(legal.astype(int), [frame["match_id"], frame["bowler_id"]]),
        over=frame["over"].to_numpy(),
    )


def _ids_seen_enough(values: pd.Series) -> dict[str, int]:
    """Give an id, from 1, to every value seen at least MIN_BALLS times. Most seen first."""
    counts = values.value_counts()
    kept = sorted(counts[counts >= MIN_BALLS].index, key=lambda value: (-counts[value], str(value)))
    return {value: index for index, value in enumerate(kept, start=1)}


def build_vocabulary(training_rows: pd.DataFrame) -> Vocabulary:
    """Built from training balls only, so the network cannot learn a name it should not know."""
    return Vocabulary(
        batters=_ids_seen_enough(training_rows["batter_id"]),
        bowlers=_ids_seen_enough(training_rows["bowler_id"]),
        venues=_ids_seen_enough(training_rows["venue"].dropna()),
        leagues={league: index
                 for index, league in enumerate(sorted(training_rows["league"].unique()), start=1)},
    )


def encode(frame: pd.DataFrame, vocabulary: Vocabulary) -> Balls:
    """Turn the frame of balls into the arrays the network reads."""
    outcome = outcome_of(frame)
    match_number = pd.factorize(frame["match_id"])[0]
    innings_key = match_number * 8 + frame["innings"].to_numpy()

    won = (frame["bat_team"] == frame["winner"]).to_numpy()
    no_winner = frame["winner"].isna().to_numpy()
    result = np.where(no_winner, 1, np.where(won, 2, 0)).astype(np.int64)

    def ids(column: str, known: dict[str, int]) -> np.ndarray:
        return frame[column].map(known).fillna(UNKNOWN).to_numpy(dtype=np.int64)

    return Balls(
        numeric=numeric_of(frame),
        history=history_of(outcome, innings_key),
        batter=ids("batter_id", vocabulary.batters),
        bowler=ids("bowler_id", vocabulary.bowlers),
        venue=ids("venue", vocabulary.venues),
        league=ids("league", vocabulary.leagues),
        fmt=frame["fmt"].map({name: index for index, name in enumerate(FORMATS)}).to_numpy(dtype=np.int64),
        outcome=outcome,
        result=result,
        year=frame["year"].to_numpy(dtype=np.int64),
        match=match_number.astype(np.int64),
    )


@dataclass
class Split:
    train: Balls
    validate: Balls
    test: Balls
    vocabulary: Vocabulary


def load_split(con: duckdb.DuckDBPyConnection) -> tuple[Split, pd.DataFrame]:
    """The three time-ordered sets, plus the raw frame for anything that needs names."""
    frame = load_frame(con)
    in_training = (frame["year"] <= TRAIN_THROUGH).to_numpy()
    vocabulary = build_vocabulary(frame[in_training])
    balls = encode(frame, vocabulary)
    split = Split(
        train=balls.where(in_training),
        validate=balls.where((frame["year"] == VALIDATE_YEAR).to_numpy()),
        test=balls.where((frame["year"] > VALIDATE_YEAR).to_numpy()),
        vocabulary=vocabulary,
    )
    return split, frame
