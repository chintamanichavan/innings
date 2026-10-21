"""Ratings that are known before a match starts: team Elo, recent form, and how good the
named players have been lately."""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

import numpy as np

AVERAGE_ELO = 1500.0
ELO_SPREAD = 400          # a side this many points ahead wins about ten times in eleven
FORM_GAMES = 10
MIN_FORM_GAMES = 3        # fewer than this and form is taken as even
HALF_LIFE_DAYS = 540      # a player's old games count half as much after this long


@dataclass(frozen=True)
class SportParams:
    elo_step: float        # how far one result moves a team's Elo
    home_edge: float       # Elo points the second-named side gets for playing at home
    carry: float           # share of a team's distance from average kept into a new year
    prior_bat: float       # chances of league-average batting mixed into a player's rate
    prior_bowl: float      # the same for bowling
    scale_bat: float       # turns a per-chance batting rate into runs per game
    scale_bowl: float      # the same for bowling


PARAMS = {
    "ck": SportParams(elo_step=20, home_edge=0, carry=0.85, prior_bat=150, prior_bowl=150,
                      scale_bat=120, scale_bowl=120),
}


def expected_score(elo_first: float, elo_second: float, home_edge: float) -> float:
    """Elo's chance that the first-named side wins. The second-named side is at home."""
    return 1 / (1 + 10 ** (-(elo_first - elo_second - home_edge) / ELO_SPREAD))


class TeamRatings:
    """Elo and recent form for every team, updated one result at a time."""

    def __init__(self, params: SportParams):
        self.params = params
        self.elo: dict = defaultdict(lambda: AVERAGE_ELO)
        self.results: dict = defaultdict(lambda: deque(maxlen=FORM_GAMES))
        self._last_year: dict = {}

    def start_of_match(self, team, year: int) -> None:
        """In a team's first match of a new year, pull its Elo part of the way back to average."""
        if self._last_year.get(team, year) != year:
            self.elo[team] = AVERAGE_ELO + self.params.carry * (self.elo[team] - AVERAGE_ELO)
        self._last_year[team] = year

    def form(self, team) -> float:
        """Share of the last ten games won, or a half when there are too few to say."""
        results = self.results[team]
        return float(np.mean(results)) if len(results) >= MIN_FORM_GAMES else 0.5

    def record(self, first, second, first_won: float) -> None:
        expected = expected_score(self.elo[first], self.elo[second], self.params.home_edge)
        change = self.params.elo_step * (first_won - expected)
        self.elo[first] += change
        self.elo[second] -= change
        self.results[first].append(first_won)
        self.results[second].append(1 - first_won)


@dataclass
class _PlayerRecord:
    bat_value: float = 0.0
    bat_chances: float = 0.0
    bowl_value: float = 0.0
    bowl_chances: float = 0.0
    day: int = 0

    def fade_to(self, day: int) -> None:
        """Shrink everything by the time passed since the record was last touched."""
        if day <= self.day:
            return
        keep = 0.5 ** ((day - self.day) / HALF_LIFE_DAYS)
        self.bat_value *= keep
        self.bat_chances *= keep
        self.bowl_value *= keep
        self.bowl_chances *= keep
        self.day = day


class PlayerRatings:
    """Each player's recent value per chance, fading with time.

    A rate is value divided by chances, with some league-average chances mixed in, so a player
    with little history sits near average. Players are keyed by (id, format): a Test record
    says little about T20.
    """

    def __init__(self, params: SportParams):
        self.params = params
        self._records: dict = {}

    def _record(self, player, day: int) -> _PlayerRecord:
        record = self._records.get(player)
        if record is None:
            record = self._records[player] = _PlayerRecord(day=day)
        record.fade_to(day)
        return record

    def batting(self, player, day: int) -> tuple[float, float]:
        """(rate, chances behind it)."""
        record = self._record(player, day)
        return record.bat_value / (record.bat_chances + self.params.prior_bat), record.bat_chances

    def bowling(self, player, day: int) -> tuple[float, float]:
        record = self._record(player, day)
        return record.bowl_value / (record.bowl_chances + self.params.prior_bowl), record.bowl_chances

    def add(self, player, day: int, bat_chances, bat_value, bowl_chances, bowl_value) -> None:
        record = self._record(player, day)
        record.bat_value += bat_value
        record.bat_chances += bat_chances
        record.bowl_value += bowl_value
        record.bowl_chances += bowl_chances

    def lineup_strength(self, lineup: list, day: int) -> tuple[float, float]:
        """A lineup's (batting, bowling) strength in runs per game above average.

        Each player counts in proportion to how much they have batted or bowled before.
        """
        def weighted(rate_of, scale: float) -> float:
            rated = [rate_of(player, day) for player in lineup]
            total_chances = sum(chances for _, chances in rated)
            if total_chances <= 0:
                return 0.0
            return scale * sum(rate * chances for rate, chances in rated) / total_chances

        return weighted(self.batting, self.params.scale_bat), weighted(self.bowling, self.params.scale_bowl)
