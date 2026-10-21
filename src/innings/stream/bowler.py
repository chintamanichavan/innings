"""The source of the stream: replays past matches into Kafka at the pace of a live game.

There is no free live ball-by-ball feed, so this plays famous close matches again. Several
"grounds" play at once, each on its own thread, so the stream always has matches side by side.
"""
from __future__ import annotations

import random
import threading
import time

from ..db import connect
from . import feed, wire

PLAYLIST = 90          # how many of the closest matches to draw from
BETWEEN_INNINGS = 8.0  # seconds
BETWEEN_MATCHES = 20.0


def _play(ground: int, grounds: int, pace: float, writer) -> None:
    time.sleep(ground * BETWEEN_MATCHES)   # do not start every ground on the same ball
    while True:
        con = connect(read_only=True)      # a fresh look each round, as the database is rebuilt
        match_ids = feed.thrillers(con, PLAYLIST)[ground::grounds]
        random.shuffle(match_ids)
        for match_id in match_ids:
            for message in feed.messages(con, [match_id]):
                kind = message["kind"]
                if kind == "innings" and message["innings"] > 1:
                    time.sleep(BETWEEN_INNINGS)
                wire.send(writer, wire.BALLS, message | {"sent_at": time.time()})
                writer.poll(0)
                if kind == "ball":
                    time.sleep(pace)
            time.sleep(BETWEEN_MATCHES)
        con.close()


def run(pace: float, grounds: int) -> None:
    wire.ensure_topics(wire.BALLS)
    writer = wire.producer()
    print(f"bowling on {grounds} grounds, one ball every {pace}s", flush=True)
    threads = [threading.Thread(target=_play, args=(ground, grounds, pace, writer), daemon=True)
               for ground in range(grounds)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
