"""The live stream. The rule that matters most: a ball scored on the stream gets exactly the
number the nightly build gave it. Kafka itself is not needed here; `innings stream bench`
runs the same check through a real broker."""
import copy

import pytest
from fastapi.testclient import TestClient

from innings.config import DB_PATH
from innings.models import cricket_limited
from innings.stream import check, feed
from innings.stream.board import Board
from innings.stream.scorer import Scorer
from innings.stream.state import MatchState
from innings.web.app import app

built = pytest.mark.skipif(not (DB_PATH.exists() and (cricket_limited.MODEL_FOLDER / "T20.joblib").exists()),
                           reason="database or win models not built")

START = dict(kind="start", match_id="m", fmt="T20", competition="IPL", year=2024, female=0,
             team1="India", team2="Australia", venue="Wankhede", date="2024-01-01")


def ball(seq, runs=0, outs=0, wide=False, noball=False, innings=1):
    return dict(kind="ball", match_id="m", seq=seq, innings=innings, over=0, ball=seq, runs=runs,
                runs_bat=runs, wide=wide, noball=noball, outs=outs)


def test_the_score_is_worked_out_from_what_happened():
    state = MatchState.from_start(START)
    state.take(dict(kind="innings", match_id="m", innings=1, balls=120, target=None))
    for message in (ball(1, runs=4), ball(2, runs=1, wide=True), ball(3, outs=1)):
        state.take(message)
    assert (state.score, state.wickets, state.balls_left, state.bat_team) == (5, 1, 118, "India")

    state.take(dict(kind="innings", match_id="m", innings=2, balls=120, target=6))
    assert (state.score, state.wickets, state.target, state.bat_team) == (0, 0, 6, "Australia")
    state.take(dict(kind="end", match_id="m", winner="Australia"))
    assert state.result == 0.0 and state.taken == 6


def test_a_ball_settles_when_the_next_one_arrives():
    records = [dict(START),
               dict(kind="innings", match_id="m", wp1=0.50),
               dict(kind="ball", match_id="m", seq=1, wp1=0.55),
               dict(kind="ball", match_id="m", seq=2, wp1=0.60),
               dict(kind="innings", match_id="m", wp1=0.40),   # the chase starting changes ball 2's worth
               dict(kind="ball", match_id="m", seq=3, wp1=0.30),
               dict(kind="end", match_id="m", wp1=1.0)]
    assert check.after_each_ball(records) == {("m", 1): 0.55, ("m", 2): 0.40, ("m", 3): 1.0}


def scored(n, kind="ball", at=100.0):
    return dict(kind=kind, match_id="m", n=n, seq=n, wp1=0.5, sent_at=at, scored_at=at)


def test_the_board_keeps_matches_in_play_and_skips_repeats():
    board = Board()
    board.take(dict(START), now=100)
    for record in (scored(1), scored(2), scored(2), scored(1)):   # a restarted scorer repeats itself
        board.take(record, now=100)
    board.take(dict(scored(1), match_id="stranger"), now=100)     # its start was never seen
    assert [point["n"] for point in board.matches["m"]["points"]] == [1, 2]
    assert [record["id"] for record in board.since(1)["records"]] == [2, 3]
    assert board.since(3)["records"] == []

    board.take(scored(3, kind="end"), now=100)
    board.tidy(now=110)
    assert "m" in board.matches            # the result stays up for a while
    board.tidy(now=1000)
    assert not board.matches


def test_a_reader_too_far_behind_is_told_to_start_again():
    board = Board()
    board.take(dict(START), now=0)
    for n in range(1, 1000):
        board.take(scored(n), now=0)
    assert board.since(5) == {"reload": True}
    assert len(board.since(990)["records"]) == 10


def test_the_stream_is_off_without_a_broker(monkeypatch):
    monkeypatch.delenv("INNINGS_KAFKA", raising=False)
    answer = TestClient(app).get("/api/stream").json()
    assert answer["on"] is False and answer["matches"] == []


@pytest.fixture(scope="module")
def sample():
    """Messages of 120 matches spread across the years, some of them cut short by rain."""
    import duckdb
    con = duckdb.connect(str(DB_PATH), read_only=True)
    every = feed.playable_ids(con)
    rained = [match_id for (match_id,) in con.execute(
        f"select match_id from ck_matches m where {feed.PLAYABLE} and m.method is not null limit 20"
    ).fetchall()]
    match_ids = sorted(set(every[::len(every) // 100] + rained))
    messages = list(feed.messages(con, match_ids))
    built_values = con.execute(
        "select match_id, seq, wp1_post from ck_ev where match_id in (select unnest(?))", [match_ids])
    want = {(match_id, seq): chance for match_id, seq, chance in built_values.fetchall()}
    con.close()
    return messages, want


@built
def test_a_match_arrives_in_order(sample):
    messages, _ = sample
    one = [message["kind"] for message in messages if message["match_id"] == messages[0]["match_id"]]
    assert one[:3] == ["start", "innings", "ball"] and one[-1] == "end" and one.count("innings") == 2
    assert not {"wp1", "target", "balls_left_pre"} & set(messages[2])   # a ball carries no answers


@built
def test_stream_equals_build(sample):
    messages, want = sample
    scorer = Scorer()
    # Odd-sized batches, so matches are cut across batches as they are on the wire.
    batches = [messages[at:at + 777] for at in range(0, len(messages), 777)]
    records = [record for batch in batches for record in scorer.score(batch)]
    got = check.after_each_ball(records)
    assert got.keys() == want.keys() and len(got) > 30_000
    assert max(abs(got[key] - want[key]) for key in want) < 1e-12
    assert not scorer.matches and scorer.dropped == 0


@built
def test_a_restarted_scorer_carries_on_where_the_last_one_stopped(sample):
    messages, want = sample
    stop = len(messages) // 2                       # part-way through a match
    first, second = Scorer(), Scorer()
    before = first.score(copy.deepcopy(messages[:stop]))
    second.catch_up(messages[:stop])                # read again from the topic, without answering
    after = second.score(messages[stop:])
    got = check.after_each_ball(before + after)
    assert max(abs(got[key] - want[key]) for key in want) < 1e-12


def test_the_push_is_never_compressed():
    """A compressing proxy holds a stream back until its buffer fills, so we forbid it."""
    import asyncio

    from innings.web.routes.stream import events

    class Gone:
        async def is_disconnected(self):
            return True

    response = asyncio.run(events(Gone(), after=0))
    assert "no-transform" in response.headers["cache-control"]
    assert response.media_type == "text/event-stream"


def delivery(over, runs=0, runs_bat=None, wide=False, noball=False, byes=0, outs=0, batter="Kohli",
             non_striker="Patidar", bowler="Bumrah", **more):
    extra = wide or noball or byes
    off_the_bat = (0 if extra else runs) if runs_bat is None else runs_bat
    return dict(kind="ball", over=over, runs=runs, runs_bat=off_the_bat,
                wide=wide, noball=noball, byes=byes, outs=outs, batter=batter, non_striker=non_striker,
                bowler=bowler, bowler_wicket=bool(outs), dismissal="caught" if outs else None,
                dismissed=batter if outs else None, fielder="Rohit" if outs else None, **more)


def test_the_scoreboard_writes_balls_the_cricket_way():
    from innings.stream.card import ball_mark, ball_words

    assert [ball_mark(delivery(0, runs)) for runs in (0, 1, 4, 6)] == ["•", "1", "4", "6"]
    assert ball_mark(delivery(0, 1, wide=True)) == "wd" and ball_mark(delivery(0, 5, wide=True)) == "5wd"
    assert ball_mark(delivery(0, 1, runs_bat=0, byes=1)) == "1lb" and ball_mark(delivery(0, outs=1)) == "W"
    assert ball_words(delivery(0, 4)) == "FOUR" and ball_words(delivery(0, 0)) == "no run"
    assert ball_words(delivery(0, 2)) == "2 runs" and ball_words(delivery(0, outs=1)) == "OUT"


def test_the_scoreboard_keeps_batters_bowler_and_over():
    from innings.stream.card import Card

    card, score, wickets = Card(), 0, 0
    over_one = [delivery(0, 0)] * 6                                  # a maiden
    over_two = [delivery(1, 4, bowler="Starc"), delivery(1, 1, wide=True, bowler="Starc"),
                delivery(1, 0, outs=1, bowler="Starc")]
    for ball in over_one + over_two:
        score, wickets = score + ball["runs"], wickets + ball["outs"]
        card.take(ball, score, wickets)
    view = card.view()
    assert card.bowlers["Bumrah"].figures() == "1-1-0-0"
    assert view["bowler"] == {"name": "Starc", "figures": "0.2-0-5-1"}
    assert view["this_over"] == ["4", "wd", "W"] and card.label == "1.2"   # the wide kept 1.2 waiting
    assert [batter["name"] for batter in view["batters"]] == ["Patidar"]  # Kohli is out
    assert view["last_wicket"] == "Kohli c Rohit b Starc 4 (8), 5/1 (1.2 ov)"
    assert view["partnership"] == [0, 0]


def test_results_read_as_a_scorecard_states_them():
    from innings.stream.scorer import result

    def chase(score, wickets, balls_left, target=181):
        state = MatchState.from_start(START)
        state.take(dict(kind="innings", match_id="m", innings=2, balls=120, target=target))
        state.score, state.wickets, state.balls_left = score, wickets, balls_left
        return state

    assert result(chase(182, 5, 8), "Australia") == "Australia won by 5 wickets (8 balls left)"
    assert result(chase(170, 10, 3), "India") == "India won by 10 runs"
    assert result(chase(179, 9, 0), "India") == "India won by 1 run"
    assert result(chase(180, 6, 0), "India") == "Match tied. India won the Super Over"


def test_a_malformed_ball_is_skipped_not_fatal():
    scorer = Scorer()
    scorer.catch_up([dict(START), dict(kind="innings", match_id="m", innings=1, balls=120, target=None)])
    broken = dict(kind="ball", match_id="m", seq=1, innings=1, runs=4)   # most of a ball is missing
    scorer.catch_up([broken])
    assert scorer.malformed == 1 and scorer.matches["m"].score == 0
