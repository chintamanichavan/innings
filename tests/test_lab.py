"""The neural network: its inputs, the exported model, the simulator and the Lab API."""
import json

import numpy as np
import pytest
from fastapi.testclient import TestClient

from innings.nn import serve
from innings.nn.data import history_of
from innings.nn.features import BALLS_SCALE, HISTORY, NUMERIC, OUTCOMES, PAD, numeric_matrix
from innings.nn.serve import Scenario
from innings.web.app import app

trained = pytest.mark.skipif(not serve.available(), reason="network not trained")
client = TestClient(app)


def get(path, **params):
    response = client.get(path, params=params)
    assert response.status_code == 200, response.text
    return response.json()


# ---- inputs ----

def test_a_ball_never_sees_itself_or_another_innings():
    outcome = np.array([1, 2, 3, 4, 5])
    innings = np.array(["a", "a", "a", "b", "b"])
    history = history_of(outcome, innings)
    assert history.shape == (5, HISTORY)
    assert (history[0] == PAD).all()                    # the first ball has nothing before it
    assert list(history[2, -2:]) == [1, 2]              # oldest first, and not the ball itself
    assert (history[3] == PAD).all()                    # a new innings starts with nothing
    assert history[4, -1] == 4 and (history[4, :-1] == PAD).all()


def test_inputs_are_finite_and_named():
    n = 3
    numeric = numeric_matrix(
        fmt=np.array(["T20", "ODI", "Test"]), innings=np.array([1, 2, 4]),
        balls_bowled=np.array([0, 150, 900]), wickets=np.array([0, 3, 9]),
        score=np.array([0, 120, 410]), target=np.array([np.nan, 281, 300]), lead=np.zeros(n),
        match_balls=np.array([0, 450, 2400]), year=np.full(n, 2025), women=np.full(n, False),
        batter_runs=np.zeros(n), batter_balls=np.zeros(n), bowler_balls=np.zeros(n), over=np.zeros(n),
    )
    assert numeric.shape == (n, len(NUMERIC))
    assert np.isfinite(numeric).all()


# ---- the honest test ----

@trained
def test_the_test_years_come_after_everything_the_network_learned_from():
    card = json.loads((serve.FOLDER / "card.json").read_text())
    evaluation = card["evaluation"]
    assert evaluation["trained_through"] < evaluation["validated_on"] < evaluation["tested_from"]
    by_name = {row["model"]: row["all"] for row in evaluation["scores"]}
    assert by_name["Network: + who is playing"] < by_name["Gradient boosting"] < by_name["League average"]


def test_the_exported_model_matches_pytorch(tmp_path):
    torch = pytest.importorskip("torch")
    pytest.importorskip("onnx")
    from innings.nn.data import Vocabulary
    from innings.nn.model import BallModel, ModelConfig, Probabilities, example_inputs
    from innings.nn.train import save_network

    torch.manual_seed(0)
    sizes = dict(batters=5, bowlers=5, venues=3, leagues=2)
    model = BallModel(ModelConfig(**sizes)).eval()
    names = {kind: {f"{kind}-{i}": i for i in range(1, size)} for kind, size in sizes.items()}
    save_network(model, Vocabulary(**names), tmp_path)

    inputs = list(example_inputs(batch=4))
    inputs[0] = torch.rand_like(inputs[0])
    inputs[1] = torch.randint(0, len(OUTCOMES), inputs[1].shape)
    with torch.no_grad():
        expected, _ = Probabilities(model)(*inputs)
    got, _ = serve.Network(tmp_path).predict(*(tensor.numpy() for tensor in inputs))
    assert np.allclose(got, expected.numpy(), atol=1e-5)


# ---- what the network says ----

@trained
def test_next_ball_chances_are_a_distribution():
    chances = serve.next_ball(serve.network(), Scenario(fmt="T20", league="IPL", balls_bowled=60, score=80))
    assert chances.shape == (len(OUTCOMES),)
    assert (chances > 0).all()
    assert abs(chances.sum() - 1) < 1e-4


@trained
def test_a_simulated_innings_obeys_the_rules_of_cricket():
    start = Scenario(fmt="T20", league="IPL", balls_bowled=90, wickets=5, score=140, target=200)
    result = serve.simulate(serve.network(), start, runs=200, seed=1)
    assert (result["score"] >= start.score).all()
    assert (result["wickets"] <= 10).all()
    assert (result["balls"] <= BALLS_SCALE["T20"]).all()
    assert ((result["score"] >= start.target) == result["reached"]).all()
    # An innings stops for one of three reasons, and only those.
    over = result["balls"] >= BALLS_SCALE["T20"]
    assert (over | (result["wickets"] == 10) | result["reached"]).all()
    again = serve.simulate(serve.network(), start, runs=200, seed=1)
    assert (again["score"] == result["score"]).all()


@trained
def test_easy_chases_are_won_and_impossible_ones_lost():
    easy = Scenario(fmt="T20", league="IPL", balls_bowled=60, wickets=1, score=150, target=152)
    hopeless = Scenario(fmt="T20", league="IPL", balls_bowled=119, wickets=5, score=100, target=200)
    net = serve.network()
    assert serve.simulate(net, easy, runs=200, seed=2)["reached"].mean() > 0.97
    assert serve.simulate(net, hopeless, runs=200, seed=2)["reached"].mean() == 0


# ---- the Lab API ----

@trained
def test_report_and_player_map():
    card = get("/api/lab")
    assert {"T20", "ODI", "Test"} == {row["format"] for row in card["evaluation"]["result"]}
    assert set(card["win_models"]) >= {"win_prob:T20", "win_prob:ODI", "win_prob:Test"}
    players = get("/api/lab/players")
    assert len(players["frames"]) == players["epochs"] + 1
    assert all(len(frame) == len(players["players"]) for frame in players["frames"])
    assert all(0 <= other < len(players["players"])
               for player in players["players"] for other in player["nearest"])


@trained
def test_matchup_and_simulation():
    kohli = get("/api/find", term="Virat Kohli")["players"][0]["player_id"]
    bumrah = get("/api/find", term="Jasprit Bumrah")["players"][0]["player_id"]
    answer = get("/api/lab/matchup", batter=kohli, bowler=bumrah, fmt="T20", phase="end")
    assert answer["batter"]["known"] and answer["bowler"]["known"]
    assert abs(sum(answer["pair"]["chances"]) - 1) < 1e-4
    assert answer["pair"]["runs_per_ball"] < answer["average"]["runs_per_ball"]   # Bumrah is hard to hit

    chase = get("/api/lab/simulate", fmt="T20", balls=90, wickets=5, score=140, target=200, seed=3)
    assert 0 < chase["win"] < 0.5
    assert chase["low"] <= chase["mean"] <= chase["high"]
    for path in chase["paths"]:
        balls = [ball for ball, _ in path]
        scores = [score for _, score in path]
        assert path[0] == [90, 140]
        assert balls == sorted(set(balls)) and balls[-1] <= chase["limit"]
        assert scores == sorted(scores)
    assert client.get("/api/lab/simulate", params={"fmt": "Test"}).status_code == 400
