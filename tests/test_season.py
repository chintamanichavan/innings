"""The season played many times over: the engine obeys cricket, the lake rows say what the
matches said, and the tally counts what it was sent. Runs on a CPU; no Kafka needed."""
import numpy as np
import pytest

torch = pytest.importorskip("torch")

from innings.nn import gpu, serve  # noqa: E402
from innings.nn.features import HISTORY, NUMERIC, PAD, WICKET, numeric_matrix  # noqa: E402
from innings.season import lake, table  # noqa: E402
from innings.season.engine import ALL_OUT, BALLS, Engine, situation  # noqa: E402
from innings.season.fixtures import Season  # noqa: E402
from innings.season.record import MOST_DELIVERIES, RECORD  # noqa: E402
from innings.season.simulate import Squads, block  # noqa: E402
from innings.season.tally import Tally  # noqa: E402

trained = pytest.mark.skipif(not serve.available(), reason="the network has not been trained")
TEAMS = 4


def made_up_season() -> Season:
    """Four teams playing each other once. Team t's players are people 11t to 11t+10."""
    sides = np.array([[a, b] for a in range(TEAMS) for b in range(a + 1, TEAMS)])
    squad = np.arange(TEAMS * 11).reshape(TEAMS, 11)
    bowling = squad[:, [10, 9, 10, 9, 8, 7, 8, 7, 6, 5, 6, 5, 4, 10, 9, 8, 7, 6, 5, 4]]
    return Season(
        year=2026, teams=[f"Team {t}" for t in range(TEAMS)],
        people=[(f"p{p}", f"Player {p}") for p in range(TEAMS * 11)],
        sides=sides, venues=np.zeros(len(sides), dtype=np.int64),
        order=squad[sides], plan=bowling[sides], usual_order=squad, usual_plan=bowling,
        playoff_venues=np.zeros(4, dtype=np.int64),
        batter_ids=np.zeros(TEAMS * 11, dtype=np.int64), bowler_ids=np.zeros(TEAMS * 11, dtype=np.int64),
        real={"champion": "Team 0", "league_wins": [3, 2, 1, 0], "playoffs": []})


@pytest.fixture(scope="module")
def played():
    """Thirty made-up seasons, as the records that would go into Kafka."""
    model, vocabulary = gpu.load(device="cpu")
    season = made_up_season()
    engine = Engine(model, 2026, vocabulary["leagues"]["IPL"], seed=1)
    records = np.concatenate(block(engine, season, Squads(season, engine.device), 0, 30,
                                   np.random.default_rng(1)))
    return season, records


@trained
def test_the_card_runs_the_same_network_as_the_site():
    model, _ = gpu.load(device="cpu")
    random = np.random.default_rng(0)
    rows = 64
    numeric = random.random((rows, len(NUMERIC))).astype(np.float32)
    history = random.integers(0, PAD + 1, (rows, HISTORY))
    batter, bowler, venue = (random.integers(0, 600, rows) for _ in range(3))
    league, fmt = random.integers(0, 11, rows), random.integers(0, 3, rows)
    want, _ = serve.network().predict(numeric, history, batter, bowler, venue, league, fmt)
    with torch.inference_mode():
        scores, _ = model(*(torch.as_tensor(values) for values in
                            (numeric, history, batter, bowler, venue, league, fmt)))
    assert np.abs(torch.softmax(scores, dim=1).numpy() - want).max() < 1e-5


def test_the_engine_sees_the_numbers_training_saw():
    random = np.random.default_rng(0)
    rows = 500
    balls, wickets = random.integers(0, 120, rows), random.integers(0, 10, rows)
    score = random.integers(0, 250, rows)
    target = np.where(random.random(rows) < 0.5, np.nan, random.integers(100, 260, rows))
    batter_runs, batter_balls = random.integers(0, 120, rows), random.integers(0, 70, rows)
    bowler_balls = random.integers(0, 24, rows)
    want = numeric_matrix(
        fmt=np.full(rows, "T20"), innings=np.where(np.isnan(target), 1, 2), balls_bowled=balls,
        wickets=wickets, score=score, target=target, lead=np.zeros(rows), match_balls=np.zeros(rows),
        year=np.full(rows, 2026), women=np.zeros(rows), batter_runs=batter_runs,
        batter_balls=batter_balls, bowler_balls=bowler_balls, over=balls // 6)

    def tensor(values):
        return torch.as_tensor(values, dtype=torch.float32)

    got = situation(balls=tensor(balls), wickets=tensor(wickets), score=tensor(score),
                    target=tensor(target), year=2026, batter_runs=tensor(batter_runs),
                    batter_balls=tensor(batter_balls), bowler_balls=tensor(bowler_balls))
    assert np.abs(got.numpy() - want).max() < 1e-6


def test_the_table_ranks_by_points_then_run_rate():
    sides = np.array([[0, 1], [2, 3], [0, 2], [1, 3], [0, 3], [1, 2]])
    winner = np.array([[0, 0, 0, 0, 0, 0]])            # the first-named side wins every match
    runs = np.full((1, 6, 2), [160, 150])
    runs[0, 1] = [220, 100]                            # team 2 thrashes team 3: best run rate on 2 points
    balls = np.full((1, 6, 2), 120)
    four = table.top_four(sides, winner, runs, balls, teams=4, random=np.random.default_rng(0))
    assert four.tolist() == [[0, 1, 2, 3]]             # 6, 4, 2 and 0 points


@trained
def test_every_innings_obeys_the_rules(played):
    season, records = played
    assert RECORD.itemsize == 9 + 4 * MOST_DELIVERIES
    assert len(records) == 30 * season.matches
    balls = lake.balls_of(records, season)
    outcomes = records["outcomes"]
    bowled = outcomes != PAD
    legal = (bowled & (outcomes < 7)).sum(axis=2)
    wickets = (outcomes == WICKET).sum(axis=2)
    assert legal.max() <= BALLS and wickets.max() <= ALL_OUT
    assert ((legal == BALLS) | (wickets == ALL_OUT))[:, 0].all()     # a first innings runs its course
    assert not (bowled[:, :, 1:] & ~bowled[:, :, :-1]).any()        # no gaps: balls, then nothing
    assert len(balls["season"]) == bowled.sum() and balls["over"].max() == 19


@trained
def test_lake_rows_name_the_right_people(played):
    season, records = played
    balls = lake.balls_of(records, season)
    # Team t's people are 11t to 11t+10, so a batter's team can be read off their number.
    assert (balls["batter"] // 11 == balls["bat_team"]).all()
    assert (balls["bowler"] // 11 != balls["bat_team"]).all()
    opening = (balls["ball"] == 0) & (balls["innings"] == 1)
    assert (balls["batter"][opening] % 11 == 0).all()               # the first ball goes to the opener
    assert (balls["bowler"][opening] % 11 == 10).all()              # from the bowler planned for over 1
    # The chasing side wins exactly when it passes the score it was set.
    runs = np.array([0, 1, 2, 3, 4, 6, 0, 1, 1, 0])[records["outcomes"]].sum(axis=2)
    chase_won = records["winner"] != records["first"]
    assert (chase_won[runs[:, 1] > runs[:, 0]]).all() and not chase_won[runs[:, 1] < runs[:, 0]].any()


@trained
def test_the_tally_counts_what_it_is_sent(played):
    season, records = played
    tally = Tally(season, target=30)
    for part in np.array_split(records, 7):            # in pieces, as it comes off the stream
        tally.take(part)
    report = tally.report(running=False)
    assert report["seasons"] == 30 and report["matches"] == len(records)
    assert report["balls"] == (records["outcomes"] != PAD).sum()
    close = dict(abs=1e-3)                             # the shares are rounded to five places
    assert sum(report["title"]) == pytest.approx(1, **close)
    assert sum(report["final"]) == pytest.approx(2, **close)
    assert sum(report["playoffs"]) == pytest.approx(4, **close)
    assert sum(report["league_wins"]) == pytest.approx(len(season.sides))
    assert [point["seasons"] for point in report["history"]] == sorted(
        point["seasons"] for point in report["history"])


def test_the_season_route_reads_what_the_job_left():
    from fastapi.testclient import TestClient

    from innings.web.app import app
    assert set(TestClient(app).get("/api/season").json()) == {"tally", "report"}
