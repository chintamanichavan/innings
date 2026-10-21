"""The figures a cricket scoreboard shows while an innings is on.

Who is at the crease and what they have made, the bowler's figures, the balls of this over,
the partnership, and how the last wicket fell: what a fan expects to see beside the score.
Like `state.py`, this is plain Python, kept up to date one message at a time.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..web.scorecard import how_out

BALLS_IN_OVER = 6


@dataclass
class Batter:
    name: str
    runs: int = 0
    balls: int = 0
    fours: int = 0
    sixes: int = 0


@dataclass
class Bowler:
    name: str
    balls: int = 0          # legal balls
    maidens: int = 0
    runs: int = 0
    wickets: int = 0
    this_over: int = 0      # runs given away in the over now being bowled

    def figures(self) -> str:
        """Overs-maidens-runs-wickets, as a scorecard writes it: 3.2-0-24-2."""
        overs = f"{self.balls // 6}" + (f".{self.balls % 6}" if self.balls % 6 else "")
        return f"{overs}-{self.maidens}-{self.runs}-{self.wickets}"


def ball_mark(ball: dict) -> str:
    """One ball as the 'this over' strip shows it: • 1 4 6 W wd 2wd nb 1lb."""
    if ball["outs"]:
        return "W"
    if ball["wide"]:
        return "wd" if ball["runs"] == 1 else f"{ball['runs']}wd"
    if ball["noball"]:
        return "nb" if ball["runs"] == 1 else f"{ball['runs']}nb"
    if ball.get("byes"):
        return f"{ball['byes']}lb" if not ball["runs_bat"] else str(ball["runs"])
    return "•" if ball["runs"] == 0 else str(ball["runs"])


def ball_words(ball: dict) -> str:
    """The result of a ball as commentary writes it: no run, 1 run, FOUR, SIX, OUT, wide."""
    if ball["outs"]:
        return "OUT"
    if ball["wide"]:
        return "wide" if ball["runs"] == 1 else f"{ball['runs']} wides"
    if ball["noball"]:
        return "no ball" if ball["runs"] == 1 else f"no ball, {ball['runs']} runs"
    if ball["runs_bat"] == 4:
        return "FOUR"
    if ball["runs_bat"] == 6:
        return "SIX"
    if ball.get("byes"):
        return f"{ball['byes']} leg bye" + ("s" if ball["byes"] > 1 else "")
    return "no run" if ball["runs"] == 0 else f"{ball['runs']} run" + ("s" if ball["runs"] > 1 else "")


@dataclass
class Card:
    batters: dict[str, Batter] = field(default_factory=dict)
    bowlers: dict[str, Bowler] = field(default_factory=dict)
    at_crease: list[str] = field(default_factory=list)   # the striker first
    bowler: str | None = None
    over: int = -1
    legal_this_over: int = 0
    this_over: list[str] = field(default_factory=list)
    partnership: list[int] = field(default_factory=lambda: [0, 0])   # runs, balls
    last_wicket: str | None = None
    label: str = "0.0"       # the ball's number as commentary writes it: over.ball, from 0.1

    def new_innings(self) -> None:
        self.__init__()

    def take(self, ball: dict, score: int, wickets: int) -> None:
        """Count one ball. `score` and `wickets` are the innings totals after it."""
        if ball["over"] != self.over:
            self.over, self.legal_this_over, self.this_over = ball["over"], 0, []
        legal = not (ball["wide"] or ball["noball"])
        # An extra ball keeps the number of the ball still to come, as commentary does.
        self.label = f"{ball['over']}.{min(self.legal_this_over + 1, BALLS_IN_OVER)}"
        self.this_over.append(ball_mark(ball))

        striker = self.batters.setdefault(ball["batter"], Batter(ball["batter"]))
        self.batters.setdefault(ball["non_striker"], Batter(ball["non_striker"]))
        striker.runs += ball["runs_bat"]
        striker.balls += not ball["wide"]
        striker.fours += ball["runs_bat"] == 4
        striker.sixes += ball["runs_bat"] == 6

        bowler = self.bowlers.setdefault(ball["bowler"], Bowler(ball["bowler"]))
        conceded = ball["runs"] - (ball.get("byes") or 0)
        bowler.runs += conceded
        bowler.this_over += conceded
        bowler.balls += legal
        bowler.wickets += bool(ball.get("bowler_wicket"))
        self.bowler = ball["bowler"]
        self.legal_this_over += legal
        if legal and self.legal_this_over == BALLS_IN_OVER:
            bowler.maidens += bowler.this_over == 0
            bowler.this_over = 0

        self.partnership[0] += ball["runs"]
        self.partnership[1] += legal
        self.at_crease = [ball["batter"], ball["non_striker"]]
        if ball["outs"]:
            out = self.batters.get(ball["dismissed"] or ball["batter"], striker)
            how = how_out(ball["dismissal"], ball.get("fielder"), ball["bowler"])
            fell_at = f"{score}/{wickets} ({self.label} ov)"
            self.last_wicket = f"{out.name} {how} {out.runs} ({out.balls}), {fell_at}"
            self.at_crease = [name for name in self.at_crease if name != out.name]
            self.partnership = [0, 0]

    def view(self) -> dict:
        """What the scoreboard shows now."""
        def batter(name: str, on_strike: bool) -> dict:
            figures = self.batters[name]
            return {"name": name, "runs": figures.runs, "balls": figures.balls, "fours": figures.fours,
                    "sixes": figures.sixes, "on_strike": on_strike}

        bowler = self.bowlers.get(self.bowler) if self.bowler else None
        return {
            "batters": [batter(name, place == 0) for place, name in enumerate(self.at_crease)],
            "bowler": {"name": bowler.name, "figures": bowler.figures()} if bowler else None,
            "this_over": list(self.this_over), "partnership": list(self.partnership),
            "last_wicket": self.last_wicket,
        }
