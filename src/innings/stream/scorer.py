"""The stream processor: reads balls, keeps every match's score, and adds the win chance.

`Scorer` is the logic and needs no Kafka, so it can be tested on its own. `run` is the loop
that feeds it from one topic and writes its answers to another.
"""
from __future__ import annotations

import copy
import signal
import sys
import time

from confluent_kafka import OFFSET_BEGINNING

from ..web import stories
from . import scoring, wire
from .card import Card, ball_words
from .state import MatchState

BATCH = 2000   # balls taken from Kafka at once; the models answer a batch almost as fast as one ball
BALL_FIELDS = {"over", "runs", "runs_bat", "wide", "noball", "outs",   # what every ball must say
               "batter", "non_striker", "bowler"}


class Scorer:
    """Remembers where every match in flight stands."""

    def __init__(self) -> None:
        self.matches: dict[str, MatchState] = {}
        self.cards: dict[str, Card] = {}   # the batters, bowler and over of each match's innings
        self.dropped = 0   # messages for a match whose start this scorer never saw
        self.malformed = 0   # messages missing what a ball must say; skipped, never fatal

    def _move(self, message: dict) -> MatchState | None:
        """Bring one match up to date with a message. None for a `start`, or an unknown match."""
        match_id, kind = message["match_id"], message["kind"]
        if kind == "start":
            self.matches[match_id] = MatchState.from_start(message)
            self.cards[match_id] = Card()
            return None
        state = self.matches.get(match_id)
        if state is None:
            self.dropped += 1
            return None
        if kind == "ball" and not message.keys() >= BALL_FIELDS:
            self.malformed += 1   # one bad message must not stop the stream, or replay will hit it again
            return None
        state.take(message)
        card = self.cards[match_id]
        if kind == "innings":
            card.new_innings()
        elif kind == "ball":
            card.take(message, state.score, state.wickets)
        elif kind == "end":
            del self.matches[match_id], self.cards[match_id]
        return state

    def catch_up(self, messages: list[dict]) -> None:
        """Rebuild the score from messages already answered, without answering them again."""
        for message in messages:
            self._move(message)

    def score(self, messages: list[dict]) -> list[dict]:
        """One record out for each message in, in the same order."""
        records, states = [], []
        for message in messages:
            state = self._move(message)
            if message["kind"] == "start":
                records.append(message)
            elif state:
                records.append(_record(message, state, self.cards.get(message["match_id"])))
                states.append(copy.copy(state))   # the match moves on within a batch; keep this moment

        chances = iter(scoring.team1_chances(states)) if states else iter(())
        now = time.time()
        for record in records:
            if record["kind"] != "start":
                record["wp1"] = next(chances)
            record["scored_at"] = now
        return records


def _record(message: dict, state: MatchState, card: Card | None) -> dict:
    """What the page needs to show a match after this message."""
    record = {"kind": message["kind"], "match_id": state.match_id, "n": state.taken, "innings": state.innings,
              "bat_team": state.bat_team, "score": state.score, "wickets": state.wickets,
              "balls_left": state.balls_left, "target": state.target, "sent_at": message.get("sent_at")}
    if message["kind"] == "ball":
        record |= {"seq": message["seq"], "at": card.label,
                   "text": f"{message['bowler']} to {message['batter']}, {ball_words(message)}",
                   "what": stories.kind(message), "card": card.view()}
    elif message["kind"] == "end":
        record["result"] = result(state, message["winner"])
    return record


def result(state: MatchState, winner: str | None) -> str:
    """The result as a scorecard states it: "Mumbai Indians won by 5 wickets (8 balls left)"."""
    if state.target is None or winner is None:
        return "No result" if winner is None else f"{winner} won"
    if state.score == state.target - 1:
        return f"Match tied. {winner} won the Super Over"
    if winner == state.team2:
        wickets, balls = 10 - state.wickets, state.balls_left
        left = f" ({balls} ball{'s' if balls != 1 else ''} left)" if balls > 0 else ""
        return f"{winner} won by {wickets} wicket{'s' if wickets != 1 else ''}{left}"
    runs = state.target - 1 - state.score
    return f"{winner} won by {runs} run{'s' if runs != 1 else ''}"


def run(group: str = "scorers", source: str = wire.BALLS, sink: str = wire.SCORED) -> None:
    """Score balls for ever. Start more of these in the same group and Kafka shares the matches out.

    A scorer keeps its matches in memory, so it loses them when it stops, and it knows nothing
    of a match that Kafka hands over from another scorer. The topic itself is the backup:
    whenever a scorer is given partitions it reads them again from the start, quietly, to
    rebuild every score, and only answers the messages no scorer has answered before.
    """
    wire.ensure_topics(source, sink)
    reader, writer = wire.consumer(group), wire.producer()
    scorer = Scorer()
    new_from: dict[int, int] = {}   # partition -> the first message not yet answered

    def rewind(consumer, partitions) -> None:
        scorer.matches.clear()
        answered = consumer.committed(partitions, timeout=10)
        for partition in answered:
            _, end = consumer.get_watermark_offsets(partition, timeout=10)
            # With nothing answered yet, or a topic that was emptied, everything there is old news.
            new_from[partition.partition] = partition.offset if 0 <= partition.offset <= end else end
            partition.offset = OFFSET_BEGINNING
        consumer.assign(answered)

    reader.subscribe([source], on_assign=rewind)
    print(f"scorer in group {group!r}: {source} -> {sink}", flush=True)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))   # so that `docker stop` runs the tidy-up below
    try:
        while True:
            messages = wire.ready(reader, BATCH, wait=0.5)
            is_old = [message.offset() < new_from[message.partition()] for message in messages]
            decoded = [wire.decode(message.value()) for message in messages]
            scorer.catch_up([message for message, old in zip(decoded, is_old, strict=True) if old])
            fresh = [message for message, old in zip(decoded, is_old, strict=True) if not old]
            for record in scorer.score(fresh):
                wire.send(writer, sink, record)
            writer.poll(0)
    finally:
        writer.flush(5)
        reader.close()   # leave the group at once, so Kafka hands these matches to another scorer
