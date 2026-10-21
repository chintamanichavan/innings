"""The network.

Each ball is described three ways, and each way has its own small encoder:

    who      a learned vector for the batter, the bowler, the ground and the league
    where    the match situation as plain numbers
    lately   the last few balls of the innings, read in order by a recurrent layer

The three are joined and passed through two hidden layers. Two heads read the result: what
happens on this ball, and how the match ends for the batting side.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import torch
from torch import nn

from .features import FORMATS, HISTORY, NUMERIC, OUTCOMES, PAD, RESULTS, UNKNOWN


@dataclass(frozen=True)
class ModelConfig:
    batters: int                 # vocabulary sizes, each including the shared UNKNOWN id
    bowlers: int
    venues: int
    leagues: int
    player_dim: int = 48         # length of the vector learned for each batter and each bowler
    venue_dim: int = 16
    league_dim: int = 8
    history_dim: int = 64
    hidden: int = 256
    dropout: float = 0.1
    use_history: bool = True     # the two switches exist for the ablation study
    use_identities: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class BallModel(nn.Module):
    def __init__(self, config: ModelConfig):
        super().__init__()
        self.config = config
        self.batter = nn.Embedding(config.batters, config.player_dim)
        self.bowler = nn.Embedding(config.bowlers, config.player_dim)
        self.venue = nn.Embedding(config.venues, config.venue_dim)
        self.league = nn.Embedding(config.leagues, config.league_dim)
        self.fmt = nn.Embedding(len(FORMATS), 4)

        self.situation = nn.Sequential(nn.Linear(len(NUMERIC), 64), nn.ReLU())
        self.past_ball = nn.Embedding(len(OUTCOMES) + 1, 16, padding_idx=PAD)
        self.recent = nn.GRU(16, config.history_dim, batch_first=True)

        identity_width = 2 * config.player_dim + config.venue_dim
        width = 64 + 4 + config.league_dim + config.history_dim + identity_width
        self.trunk = nn.Sequential(
            nn.Linear(width, config.hidden), nn.ReLU(), nn.Dropout(config.dropout),
            nn.Linear(config.hidden, config.hidden), nn.ReLU(), nn.Dropout(config.dropout),
        )
        self.outcome_head = nn.Linear(config.hidden, len(OUTCOMES))
        self.result_head = nn.Linear(config.hidden, len(RESULTS))

    def forward(self, numeric, history, batter, bowler, venue, league, fmt):
        """Returns unnormalised scores: (outcome [batch, 9], result [batch, 3])."""
        if self.config.use_history:
            _, last_hidden = self.recent(self.past_ball(history))
            lately = last_hidden[-1]
        else:
            lately = numeric.new_zeros(numeric.shape[0], self.config.history_dim)

        who = torch.cat([self.batter(batter), self.bowler(bowler), self.venue(venue)], dim=1)
        if not self.config.use_identities:
            who = torch.zeros_like(who)

        joined = torch.cat([self.situation(numeric), self.fmt(fmt), self.league(league), lately, who], dim=1)
        hidden = self.trunk(joined)
        return self.outcome_head(hidden), self.result_head(hidden)


class Probabilities(nn.Module):
    """The model as the site uses it: the same inputs, probabilities out. This is what is exported."""

    def __init__(self, model: BallModel):
        super().__init__()
        self.model = model

    def forward(self, numeric, history, batter, bowler, venue, league, fmt):
        outcome, result = self.model(numeric, history, batter, bowler, venue, league, fmt)
        return torch.softmax(outcome, dim=1), torch.softmax(result, dim=1)


INPUT_NAMES = ["numeric", "history", "batter", "bowler", "venue", "league", "fmt"]
OUTPUT_NAMES = ["outcome", "result"]


def example_inputs(batch: int = 2) -> tuple:
    """Inputs of the right shapes and types, for exporting and for tests."""
    ids = torch.full((batch,), UNKNOWN, dtype=torch.long)
    return (torch.zeros(batch, len(NUMERIC)), torch.full((batch, HISTORY), PAD, dtype=torch.long),
            ids, ids, ids, ids, ids)
