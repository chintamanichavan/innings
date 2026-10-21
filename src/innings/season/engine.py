"""The match engine: the network plays many T20 innings at once on a graphics card.

Every row of every tensor here is one innings in one simulated season. A step bowls one
ball in all of them together: ask the network what could happen, draw one outcome for each
innings from its own chances, and move each score on. Nothing here knows about seasons,
tables or Kafka.
"""
from __future__ import annotations

from dataclasses import dataclass

import torch

from ..nn.features import (
    BALLS_SCALE,
    FORMATS,
    HISTORY,
    OUTCOME_IS_LEGAL,
    OUTCOME_RUNS,
    PAD,
    SCORE_SCALE,
    WICKET,
    WIDE,
)
from ..nn.model import BallModel
from .record import MOST_DELIVERIES

FMT = "T20"
BALLS = int(BALLS_SCALE[FMT])
SCORE = SCORE_SCALE[FMT]
ALL_OUT = 10


@dataclass
class Innings:
    """How a batch of innings went. One row each."""
    score: torch.Tensor       # [rows]
    wickets: torch.Tensor
    balls: torch.Tensor       # legal balls bowled
    outcomes: torch.Tensor    # [rows, MOST_DELIVERIES] what each delivery was; PAD after the end
    strikers: torch.Tensor    # [rows, MOST_DELIVERIES] the facing batter's place in the order


def situation(*, balls, wickets, score, target, year: int, batter_runs, batter_balls,
              bowler_balls) -> torch.Tensor:
    """The numeric inputs for one ball of many T20 innings: the columns of `features.NUMERIC`.

    This is `features.numeric_matrix` again, for one format and on the graphics card. A test
    holds the two to the same numbers.
    """
    chasing = ~torch.isnan(target)
    need = torch.where(chasing, (torch.nan_to_num(target) - score).clamp(min=0), torch.zeros_like(score))
    zero = torch.zeros_like(score)
    columns = [
        balls / BALLS,
        wickets / 10.0,
        score / SCORE,
        (score / balls.clamp(min=6)).clamp(max=3.0),
        chasing.float(),
        need / SCORE,
        torch.where(chasing, (need / (BALLS - balls).clamp(min=1)).clamp(max=3.0), zero),
        zero, zero,                 # lead and match progress: Tests only
        chasing.float(), zero, zero,   # second innings; there is no third or fourth
        torch.full_like(score, (year - 2015) / 10.0),
        zero,                       # women
        (batter_runs / 50.0).clamp(max=4.0),
        (batter_balls / 30.0).clamp(max=6.0),
        (bowler_balls / 24.0).clamp(max=6.0),
        ((balls // 6) % 10) / 10.0,
    ]
    return torch.stack(columns, dim=1)


class Engine:
    def __init__(self, model: BallModel, year: int, league: int, seed: int = 0):
        self.model = model
        self.device = next(model.parameters()).device
        self.year, self.league = year, league
        self.random = torch.Generator(device=self.device).manual_seed(seed)
        self.runs = torch.as_tensor(OUTCOME_RUNS, device=self.device)
        self.legal = torch.as_tensor(OUTCOME_IS_LEGAL, device=self.device).bool()

    @torch.inference_mode()
    def innings(self, batters: torch.Tensor, bowlers: torch.Tensor, earlier_overs: torch.Tensor,
                venue: torch.Tensor, target: torch.Tensor) -> Innings:
        """Bat out a batch of innings.

        batters        [rows, 11] the network's batter ids, in batting order
        bowlers        [rows, 20] the network's bowler id for each over
        earlier_overs  [rows, 20] overs the same bowler has already bowled before each over
        venue          [rows]     the network's ground id
        target         [rows]     runs needed to win; NaN when batting first
        """
        rows, device = len(batters), self.device
        row = torch.arange(rows, device=device)
        league = torch.full((rows,), self.league, device=device)
        fmt = torch.full((rows,), FORMATS.index(FMT), device=device)

        balls = torch.zeros(rows, dtype=torch.long, device=device)
        wickets, score = torch.zeros_like(balls), torch.zeros_like(balls)
        history = torch.full((rows, HISTORY), PAD, dtype=torch.long, device=device)
        at_crease = torch.tensor([0, 1], device=device).repeat(rows, 1)   # column 0 is on strike
        next_in = torch.full((rows,), 2, device=device)
        batter_runs = torch.zeros((rows, 11), dtype=torch.long, device=device)
        batter_balls = torch.zeros_like(batter_runs)
        outcomes = torch.full((rows, MOST_DELIVERIES), PAD, dtype=torch.uint8, device=device)
        strikers = torch.zeros((rows, MOST_DELIVERIES), dtype=torch.uint8, device=device)

        for delivery in range(MOST_DELIVERIES):
            live = (balls < BALLS) & (wickets < ALL_OUT) & ~(score >= target)
            if not live.any():
                break
            over = (balls // 6).clamp(max=19).unsqueeze(1)
            striker = at_crease[:, 0]
            numeric = situation(
                balls=balls.float(), wickets=wickets.float(), score=score.float(), target=target,
                year=self.year, batter_runs=batter_runs[row, striker].float(),
                batter_balls=batter_balls[row, striker].float(),
                bowler_balls=(earlier_overs.gather(1, over).squeeze(1) * 6 + balls % 6).float())
            scores, _ = self.model(numeric, history, batters[row, striker],
                                   bowlers.gather(1, over).squeeze(1), venue, league, fmt)
            drawn = torch.multinomial(torch.softmax(scores, dim=1), 1, generator=self.random).squeeze(1)

            outcomes[:, delivery] = torch.where(live, drawn, PAD).to(torch.uint8)
            strikers[:, delivery] = striker.to(torch.uint8)
            legal = live & self.legal[drawn]
            out = live & (drawn == WICKET)
            faced = live & (drawn != WIDE)
            off_the_bat = torch.where(faced & (drawn < WICKET), self.runs[drawn], 0)

            score = score + torch.where(live, self.runs[drawn], 0)
            balls = balls + legal
            wickets = wickets + out
            moved_on = torch.cat([history[:, 1:], drawn.unsqueeze(1)], dim=1)
            history = torch.where(live.unsqueeze(1), moved_on, history)
            batter_runs[row, striker] += off_the_bat
            batter_balls[row, striker] += faced
            # The next batter in the order takes the place of the one who is out.
            at_crease[:, 0] = torch.where(out, next_in.clamp(max=10), striker)
            next_in = next_in + out
            # The batters cross on an odd number of runs, and again when the over ends.
            cross = (faced & (off_the_bat % 2 == 1)) ^ (legal & (balls % 6 == 0))
            at_crease = torch.where(cross.unsqueeze(1), at_crease.flip(1), at_crease)

        return Innings(score, wickets, balls, outcomes, strikers)
