"""Where one match stands, kept up to date one ball at a time.

This is the memory of the stream. A ball message says only what happened: runs, a wicket,
a wide. The score, the wickets down and the balls left are all worked out here.
Nothing in this file knows about Kafka or about the models.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MatchState:
    match_id: str
    fmt: str            # T20 or ODI
    competition: str
    year: int
    female: int
    team1: str          # bats first
    team2: str
    innings: int = 1
    score: int = 0
    wickets: int = 0
    balls_left: int = 0
    target: int | None = None       # runs the chasing side needs
    result: float | None = None     # team1's result once the match is over: 1, 0, or 0.5
    taken: int = 0                  # messages so far; numbers this match's records in order

    @classmethod
    def from_start(cls, message: dict) -> MatchState:
        return cls(*(message[name] for name in
                     ("match_id", "fmt", "competition", "year", "female", "team1", "team2")))

    @property
    def bat_team(self) -> str:
        return self.team1 if self.innings == 1 else self.team2

    def take(self, message: dict) -> None:
        """Move the match on by one message: an innings starting, a ball, or the result."""
        kind = message["kind"]
        self.taken += 1
        if kind == "innings":
            self.innings, self.target = message["innings"], message["target"]
            self.balls_left, self.score, self.wickets = message["balls"], 0, 0
        elif kind == "ball":
            self.score += message["runs"]
            self.wickets += message["outs"]
            self.balls_left -= not (message["wide"] or message["noball"])
        elif kind == "end":
            winner = message["winner"]
            self.result = 0.5 if winner is None else float(winner == self.team1)

    def before_next_ball(self) -> dict:
        """The state as the models want it: the columns of a ball that is about to be bowled."""
        wickets = min(self.wickets, 9)   # all out: the innings is over, and a new one is about to start
        return {"innings": self.innings, "score_pre": self.score, "wkts_pre": wickets,
                "balls_left_pre": self.balls_left, "target": self.target or 0, "year": self.year,
                "female": self.female}
