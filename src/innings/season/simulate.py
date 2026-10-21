"""Play one real season again, many thousands of times, and send every match into Kafka.

Seasons are played in blocks on the graphics card: every league match of every season in the
block at once, then the four playoff matches between whichever teams each season's table sent
through. Each finished match becomes one message.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
import torch

from ..nn.features import PAD
from .engine import Engine
from .fixtures import Season
from .record import RECORD, end_marker
from .table import FULL_INNINGS, top_four

BLOCK = 1000   # seasons played at once; 70,000 innings fill about half of a 16 GB card


@dataclass
class Played:
    """A batch of finished matches. Everything is indexed by row; sides are 0 (home) and 1 (away)."""
    first: np.ndarray       # [rows] the side that batted first
    winner: np.ndarray      # [rows] the side that won
    runs: np.ndarray        # [rows, 2] by side
    balls: np.ndarray       # [rows, 2] balls faced by side, a side bowled out counting as 120
    outcomes: np.ndarray    # [rows, 2, deliveries] by innings
    strikers: np.ndarray


class Squads:
    """The season's players on the graphics card, as the network's ids."""

    def __init__(self, season: Season, device: torch.device):
        def on_card(values: np.ndarray) -> torch.Tensor:
            return torch.as_tensor(values, device=device)

        self.batters = on_card(season.batter_ids[season.order])           # [match, side, 11]
        self.bowlers = on_card(season.bowler_ids[season.plan])            # [match, side, 20]
        self.earlier = _earlier_overs(on_card(season.plan))
        self.venues = on_card(season.venues)
        self.usual_batters = on_card(season.batter_ids[season.usual_order])   # [team, 11]
        self.usual_bowlers = on_card(season.bowler_ids[season.usual_plan])
        self.usual_earlier = _earlier_overs(on_card(season.usual_plan))
        self.playoff_venues = on_card(season.playoff_venues)


def _earlier_overs(plan: torch.Tensor) -> torch.Tensor:
    """For each over of a bowling plan, how many overs its bowler has already bowled."""
    same_bowler = plan.unsqueeze(-1) == plan.unsqueeze(-2)                # [..., over, other over]
    before = torch.ones(plan.shape[-1], plan.shape[-1], dtype=torch.bool, device=plan.device).tril(-1)
    return (same_bowler & before).sum(-1)


def play(engine: Engine, batters, bowlers, earlier, venue) -> Played:
    """Play a batch of matches. `batters`, `bowlers` and `earlier` are [rows, side, ...]."""
    rows = len(venue)
    row = torch.arange(rows, device=venue.device)
    first = torch.randint(0, 2, (rows,), device=venue.device, generator=engine.random)   # the toss
    second = 1 - first
    batting_first = engine.innings(batters[row, first], bowlers[row, second], earlier[row, second], venue,
                                   torch.full((rows,), torch.nan, device=venue.device))
    chase = engine.innings(batters[row, second], bowlers[row, first], earlier[row, first], venue,
                           (batting_first.score + 1).float())

    # A tie goes to a super over, which we settle with a coin.
    coin = torch.randint(0, 2, (rows,), device=venue.device, generator=engine.random)
    winner = torch.where(chase.score > batting_first.score, second,
                         torch.where(chase.score == batting_first.score, coin, first))
    runs = torch.zeros((rows, 2), dtype=torch.long, device=venue.device)
    balls = torch.zeros_like(runs)
    for side, innings in ((first, batting_first), (second, chase)):
        runs[row, side] = innings.score
        balls[row, side] = torch.where(innings.wickets >= 10, FULL_INNINGS, innings.balls)
    return Played(*(tensor.cpu().numpy() for tensor in (
        first, winner, runs, balls,
        torch.stack([batting_first.outcomes, chase.outcomes], dim=1),
        torch.stack([batting_first.strikers, chase.strikers], dim=1))))


def _records(first_season: int, match: np.ndarray, home: np.ndarray, away: np.ndarray,
             played: Played, seasons: int) -> np.ndarray:
    """Finished matches as records. Rows run season by season: season 0's matches, then season 1's."""
    records = np.zeros(len(match), dtype=RECORD)
    records["season"] = first_season + np.arange(len(match)) // (len(match) // seasons)
    records["match"], records["home"], records["away"] = match, home, away
    records["first"], records["winner"] = played.first, played.winner
    records["outcomes"], records["strikers"] = played.outcomes, played.strikers
    return records


def block(engine: Engine, season: Season, squads: Squads, first_season: int, seasons: int,
          random: np.random.Generator) -> list[np.ndarray]:
    """Play `seasons` whole seasons. Returns their matches as records, league first, then playoffs."""
    league_matches = len(season.sides)
    match = torch.arange(league_matches, device=engine.device).repeat(seasons)
    league = play(engine, squads.batters[match], squads.bowlers[match], squads.earlier[match],
                  squads.venues[match])
    match = match.cpu().numpy()
    out = [_records(first_season, match, season.sides[match, 0], season.sides[match, 1], league, seasons)]

    def by_season(values: np.ndarray) -> np.ndarray:
        return values.reshape(seasons, league_matches, *values.shape[1:])

    table = top_four(season.sides, by_season(league.winner), by_season(league.runs),
                     by_season(league.balls), len(season.teams), random)

    def knockout(number: int, home: np.ndarray, away: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Play one playoff match in every season. Returns (winners, losers) as team numbers."""
        teams = torch.as_tensor(np.stack([home, away], axis=1), device=engine.device)
        played = play(engine, squads.usual_batters[teams], squads.usual_bowlers[teams],
                      squads.usual_earlier[teams], squads.playoff_venues[number].expand(seasons))
        stage = np.full(seasons, league_matches + number)
        out.append(_records(first_season, stage, home, away, played, seasons))
        return np.where(played.winner == 0, home, away), np.where(played.winner == 0, away, home)

    first_finalist, second_chance = knockout(0, table[:, 0], table[:, 1])    # Qualifier 1
    survivor, _ = knockout(1, table[:, 2], table[:, 3])                      # Eliminator
    second_finalist, _ = knockout(2, second_chance, survivor)                # Qualifier 2
    knockout(3, first_finalist, second_finalist)                             # Final
    return out


def run(engine: Engine, season: Season, seasons: int, send, seed: int = 0) -> dict:
    """Play `seasons` seasons, handing each record's bytes to `send(season number, payload)`.

    Returns what was made: matches, balls, and the seconds spent playing and sending.
    """
    squads = Squads(season, engine.device)
    random = np.random.default_rng(seed)
    matches = balls = 0
    playing = sending = 0.0
    for first_season in range(0, seasons, BLOCK):
        size = min(BLOCK, seasons - first_season)
        started = time.time()
        made = block(engine, season, squads, first_season, size, random)
        playing += time.time() - started
        started = time.time()
        for records in made:
            matches += len(records)
            balls += int((records["outcomes"] != PAD).sum())
            payload = records.tobytes()
            for at, number in enumerate(records["season"].tolist()):
                send(number, payload[at * RECORD.itemsize:(at + 1) * RECORD.itemsize])
        sending += time.time() - started
    return {"seasons": seasons, "matches": matches, "balls": balls,
            "playing_seconds": round(playing, 2), "sending_seconds": round(sending, 2)}


__all__ = ["block", "end_marker", "play", "run"]
