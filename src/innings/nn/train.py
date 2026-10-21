"""Train the network, test it honestly, and write everything the site needs.

Run with `innings train`. It needs the `train` extra and a GPU helps: about a minute per model.

What gets written, under data/nn/:
    model.onnx        the trained network, runnable without PyTorch
    vocabulary.json   which id each player, ground and league was given
    card.json         what it was trained on, how it scored, and against what
    players.json      where the network places each batter, epoch by epoch, and who is nearby
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, replace

import duckdb
import numpy as np
import pandas as pd
import torch
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import cross_val_score
from torch import nn

from ..config import DATA
from .data import (
    MIN_BALLS,
    TRAIN_THROUGH,
    VALIDATE_YEAR,
    Balls,
    Split,
    Vocabulary,
    build_vocabulary,
    encode,
    load_split,
)
from .features import FORMATS, HISTORY, NUMERIC, OUTCOMES, UNKNOWN, WICKET
from .model import INPUT_NAMES, OUTPUT_NAMES, BallModel, ModelConfig, Probabilities, example_inputs

OUT = DATA / "nn"
SEED = 7


@dataclass(frozen=True)
class TrainConfig:
    epochs: int = 16               # chosen on the validation year: 8, 16 and 24 score within 0.001
    batch: int = 8192
    learning_rate: float = 3e-3
    weight_decay: float = 1e-4
    hide_identity: float = 0.15    # share of training balls whose player is hidden, to learn "unknown"
    result_weight: float = 0.3     # how much the match-result head counts beside the next-ball head


# The network is trained three times, each time shown more, to see what each part adds.
ABLATIONS = [
    ("situation only", dict(use_history=False, use_identities=False)),
    ("+ recent balls", dict(use_history=True, use_identities=False)),
    ("+ who is playing", dict(use_history=True, use_identities=True)),
]
MAP_PLAYERS = 500          # batters shown on the map: the ones with the most training balls
MAP_MIN_BALLS = 1500
NEIGHBOURS = 6


# ---- moving data to the GPU ----

def to_device(balls: Balls, device: str) -> dict[str, torch.Tensor]:
    """All of a set on the device at once. It fits: the largest set is a few hundred megabytes."""
    return {
        "numeric": torch.from_numpy(balls.numeric).to(device),
        "history": torch.from_numpy(balls.history.astype(np.uint8)).to(device),
        **{name: torch.from_numpy(getattr(balls, name)).to(device)
           for name in ("batter", "bowler", "venue", "league", "fmt", "outcome", "result")},
    }


def model_inputs(tensors: dict[str, torch.Tensor], rows) -> list[torch.Tensor]:
    inputs = [tensors[name][rows] for name in INPUT_NAMES]
    inputs[1] = inputs[1].long()   # history is stored small and widened one batch at a time
    return inputs


# ---- training ----

@torch.no_grad()
def predict(model: BallModel, tensors: dict[str, torch.Tensor],
            batch: int = 65536) -> tuple[np.ndarray, np.ndarray]:
    """Outcome and result probabilities for every ball in a set."""
    model.eval()
    outcome, result = [], []
    for start in range(0, len(tensors["outcome"]), batch):
        rows = slice(start, start + batch)
        outcome_scores, result_scores = model(*model_inputs(tensors, rows))
        outcome.append(torch.softmax(outcome_scores, dim=1).cpu().numpy())
        result.append(torch.softmax(result_scores, dim=1).cpu().numpy())
    return np.concatenate(outcome), np.concatenate(result)


def log_loss(probabilities: np.ndarray, truth: np.ndarray) -> float:
    """The average surprise, in nats, at what actually happened. Lower is better."""
    chosen = probabilities[np.arange(len(truth)), truth]
    return float(-np.log(np.clip(chosen, 1e-9, 1.0)).mean())


def train_one(config: ModelConfig, train: dict, settings: TrainConfig, device: str, *,
              validate: dict | None = None, validate_truth: np.ndarray | None = None,
              keep_snapshots: bool = False) -> dict:
    """Train one network.

    With a validation set, the weights kept are from the epoch that scored best on it. Without
    one, every epoch is used and the last is kept: that is how the deployed model is fitted,
    once the number of epochs has been settled.
    """
    torch.manual_seed(SEED)
    model = BallModel(config).to(device)
    optimiser = torch.optim.AdamW(model.parameters(), lr=settings.learning_rate,
                                  weight_decay=settings.weight_decay)
    rows = len(train["outcome"])
    steps = settings.epochs * (rows // settings.batch)
    schedule = torch.optim.lr_scheduler.OneCycleLR(optimiser, max_lr=settings.learning_rate,
                                                   total_steps=steps)
    loss_of = nn.CrossEntropyLoss()

    snapshots = [model.batter.weight.detach().cpu().numpy().copy()] if keep_snapshots else []
    curve, best = [], dict(loss=float("inf"), state=None, epoch=0)
    for epoch in range(1, settings.epochs + 1):
        model.train()
        order = torch.randperm(rows, device=device)
        running = 0.0
        for step in range(rows // settings.batch):
            picked = order[step * settings.batch:(step + 1) * settings.batch]
            inputs = model_inputs(train, picked)
            # Hide some players, so the network learns what to say about one it has never met.
            for position in (2, 3, 4):   # batter, bowler, ground
                hidden = torch.rand(len(picked), device=device) < settings.hide_identity
                inputs[position] = inputs[position].masked_fill(hidden, UNKNOWN)
            outcome_scores, result_scores = model(*inputs)
            loss = (loss_of(outcome_scores, train["outcome"][picked])
                    + settings.result_weight * loss_of(result_scores, train["result"][picked]))
            optimiser.zero_grad(set_to_none=True)
            loss.backward()
            optimiser.step()
            schedule.step()
            running += loss.item()
        point = dict(epoch=epoch, train=running / (rows // settings.batch))
        if keep_snapshots:
            snapshots.append(model.batter.weight.detach().cpu().numpy().copy())
        if validate is not None:
            point["validate"] = log_loss(predict(model, validate)[0], validate_truth)
            if point["validate"] < best["loss"]:
                weights = {name: value.detach().clone() for name, value in model.state_dict().items()}
                best = dict(loss=point["validate"], epoch=epoch, state=weights)
        curve.append(point)
    if validate is None:
        return dict(model=model, curve=curve, best_epoch=settings.epochs, snapshots=snapshots)
    model.load_state_dict(best["state"])
    return dict(model=model, curve=curve, best_epoch=best["epoch"], snapshots=snapshots)


# ---- baselines: what the network has to beat ----

def league_average(train: Balls, test: Balls) -> np.ndarray:
    """Predict the same thing for every ball: how often each outcome happens in that format."""
    table = np.zeros((len(FORMATS), len(OUTCOMES)))
    for fmt in range(len(FORMATS)):
        table[fmt] = np.bincount(train.outcome[train.fmt == fmt], minlength=len(OUTCOMES)) + 1
    table /= table.sum(axis=1, keepdims=True)
    return table[test.fmt]


def situation_table(train: Balls, test: Balls) -> np.ndarray:
    """A lookup by format, phase of the innings and wickets down: what an analyst might tabulate."""
    def cell(balls: Balls) -> np.ndarray:
        phase = np.minimum((balls.numeric[:, 0] * 5).astype(int), 4)
        wickets = np.minimum((balls.numeric[:, 1] * 10).round().astype(int) // 2, 4)
        return balls.fmt * 25 + phase * 5 + wickets

    table = np.ones((len(FORMATS) * 25, len(OUTCOMES)))
    np.add.at(table, (cell(train), train.outcome), 1)
    table /= table.sum(axis=1, keepdims=True)
    return table[cell(test)]


def boosted_trees(train: Balls, test: Balls, sample: int = 1_500_000) -> np.ndarray:
    """Gradient boosting on the same situation numbers: the strong, standard tabular method."""
    def inputs(balls: Balls) -> np.ndarray:
        return np.column_stack([balls.numeric, balls.fmt, balls.league])

    picked = np.random.default_rng(SEED).choice(len(train), size=min(sample, len(train)), replace=False)
    model = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.1, max_leaf_nodes=63,
                                           random_state=SEED)
    model.fit(inputs(train)[picked], train.outcome[picked])
    probabilities = np.zeros((len(test), len(OUTCOMES)))
    probabilities[:, model.classes_] = model.predict_proba(inputs(test))
    return np.clip(probabilities, 1e-9, 1.0)


# ---- the honest test ----

def score(name: str, probabilities: np.ndarray, test: Balls, known: np.ndarray) -> dict:
    """Log loss overall, by format, and on balls where the network knows both players."""
    row = dict(model=name, all=log_loss(probabilities, test.outcome),
               known_players=log_loss(probabilities[known], test.outcome[known]))
    for index, fmt in enumerate(FORMATS):
        mask = test.fmt == index
        row[fmt] = log_loss(probabilities[mask], test.outcome[mask])
    return row


def calibration(probabilities: np.ndarray, truth: np.ndarray, outcome: int, bins: int = 12) -> list[dict]:
    """Group balls by the stated chance of one outcome; compare with how often it happened."""
    stated, happened = probabilities[:, outcome], (truth == outcome).astype(float)
    edges = np.quantile(stated, np.linspace(0, 1, bins + 1))
    group = np.clip(np.searchsorted(edges, stated, side="right") - 1, 0, bins - 1)
    return [dict(stated=float(stated[group == g].mean()), happened=float(happened[group == g].mean()),
                 n=int((group == g).sum())) for g in range(bins) if (group == g).any()]


def result_scores(result_probabilities: np.ndarray, test: Balls) -> list[dict]:
    """How well the match-result head calls decided matches: accuracy and Brier score by format."""
    points = result_probabilities[:, 2] + 0.5 * result_probabilities[:, 1]   # a win is 1, no winner a half
    rows = []
    for index, fmt in enumerate(FORMATS):
        decided = (test.fmt == index) & (test.result != 1)
        won = (test.result[decided] == 2).astype(float)
        rows.append(dict(format=fmt, balls=int(decided.sum()),
                         accuracy=float(((points[decided] > 0.5) == (won == 1)).mean()),
                         brier=float(((points[decided] - won) ** 2).mean())))
    return rows


# ---- what the network learned about players ----

def batters_for_map(training: pd.DataFrame, vocabulary: Vocabulary,
                    con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """The best-known batters in the balls a model was trained on, with the plain stats the
    network was never shown directly."""
    faced = training[~training["wide"]]
    stats = faced.groupby("batter_id").agg(balls=("runs_bat", "size"), runs=("runs_bat", "sum"))
    stats["outs"] = training[training["outs"] > 0].groupby("batter_id").size()
    stats["boundaries"] = faced[faced["runs_bat"] >= 4].groupby("batter_id").size()
    stats = stats.fillna(0)
    stats = stats[stats["balls"] >= MAP_MIN_BALLS].sort_values("balls", ascending=False).head(MAP_PLAYERS)
    stats["strike_rate"] = 100 * stats["runs"] / stats["balls"]
    stats["balls_per_out"] = stats["balls"] / stats["outs"].clip(lower=1)
    stats["boundary_rate"] = 100 * stats["boundaries"] / stats["balls"]
    names = dict(con.execute("select player_id, name from ck_players").fetchall())
    stats["name"] = [names.get(player, player) for player in stats.index]
    stats["id"] = [vocabulary.batters[player] for player in stats.index]
    return stats.reset_index()


def flatten(vectors: np.ndarray, basis_from: np.ndarray) -> np.ndarray:
    """Project vectors onto the two directions in which `basis_from` varies most (PCA)."""
    centre = basis_from.mean(axis=0)
    _, _, directions = np.linalg.svd(basis_from - centre, full_matrices=False)
    return (vectors - centre) @ directions[:2].T


def what_vectors_know(vectors: np.ndarray, batters: pd.DataFrame) -> list[dict]:
    """Can a straight line read a plain stat off the learned vectors? Cross-validated R squared.

    The network was never given these stats. If a linear readout recovers them, it worked
    them out from the balls alone.
    """
    out = []
    for column, label in (("strike_rate", "strike rate"), ("balls_per_out", "balls per dismissal"),
                          ("boundary_rate", "boundary rate")):
        r_squared = cross_val_score(RidgeCV(alphas=np.logspace(-2, 3, 12)), vectors, batters[column],
                                    cv=5, scoring="r2").mean()
        out.append(dict(stat=label, r_squared=float(r_squared)))
    return out


def player_file(snapshots: list[np.ndarray], batters: pd.DataFrame, best_epoch: int) -> dict:
    """Where each batter sits on the map after every epoch, and who ends up nearest."""
    ids = batters["id"].to_numpy()
    final = snapshots[best_epoch][ids]
    unit = final / np.linalg.norm(final, axis=1, keepdims=True)
    closeness = unit @ unit.T
    np.fill_diagonal(closeness, -1)
    nearest = np.argsort(-closeness, axis=1)[:, :NEIGHBOURS]

    frames = [flatten(snapshot[ids], final) for snapshot in snapshots]
    scale = np.abs(frames[best_epoch]).max()
    return dict(
        epochs=len(snapshots) - 1, best_epoch=best_epoch,
        players=[dict(id=row.batter_id, name=row.name, balls=int(row.balls),
                      strike_rate=round(row.strike_rate, 1),
                      balls_per_out=round(row.balls_per_out, 1), boundary_rate=round(row.boundary_rate, 1),
                      nearest=[int(n) for n in nearest[index]])
                 for index, row in enumerate(batters.itertuples())],
        frames=[np.round(frame / scale, 4).tolist() for frame in frames],
        probes=what_vectors_know(final, batters),
    )


# ---- can it play a whole innings? ----

REALITY_CHECKS = [("IPL", "T20"), ("T20I", "T20"), ("ODI", "ODI")]
SIMULATED_INNINGS = 3000


def simulated_vs_real(con: duckdb.DuckDBPyConnection, folder) -> list[dict]:
    """Let a saved network bat a whole first innings many times; compare the totals with real ones.

    Nobody told the network what a total looks like. It only ever learned one ball at a time.
    If its made-up innings have the right average and the right spread, the ball-by-ball
    probabilities add up to something true. Real totals are from the test years. The made-up
    sides are all average players, so some shortfall against real line-ups is expected.
    """
    from .serve import Network, Scenario, simulate  # the saved model, exactly as the site runs it

    net = Network(folder)
    rows = []
    for league, fmt in REALITY_CHECKS:
        real = con.execute("""
            select score1 from ck_matches
            where competition = ? and gender = 'male' and year > ? and (balls1 = max_balls or wkts1 = 10)
        """, [league, VALIDATE_YEAR]).df()["score1"]
        scenario = Scenario(fmt, league=league, year=VALIDATE_YEAR + 1)
        made_up = simulate(net, scenario, runs=SIMULATED_INNINGS, seed=SEED)["score"]
        rows.append(dict(league=league, real_innings=len(real),
                         real_mean=float(real.mean()), real_spread=float(real.std()),
                         simulated_mean=float(made_up.mean()), simulated_spread=float(made_up.std())))
    return rows


# ---- saving ----

def save_network(model: BallModel, vocabulary: Vocabulary, folder) -> None:
    """Write a network in a portable format with the ids it knows, so it runs without PyTorch."""
    folder.mkdir(parents=True, exist_ok=True)
    wrapped = Probabilities(model).cpu().eval()
    torch.onnx.export(
        wrapped, example_inputs(), str(folder / "model.onnx"), input_names=INPUT_NAMES,
        output_names=OUTPUT_NAMES, dynamo=False, opset_version=17,
        dynamic_axes={name: {0: "batch"} for name in INPUT_NAMES + OUTPUT_NAMES},
    )
    (folder / "vocabulary.json").write_text(json.dumps(vars(vocabulary)))


# ---- the two jobs: an honest test, then the model the site uses ----

def evaluate(split: Split, con: duckdb.DuckDBPyConnection, settings: TrainConfig, device: str) -> dict:
    """Train on the past, test on seasons never seen, and compare with simpler methods."""
    train, validate, test = (to_device(balls, device) for balls in (split.train, split.validate, split.test))
    known = (split.test.batter != UNKNOWN) & (split.test.bowler != UNKNOWN)
    base = ModelConfig(**split.vocabulary.sizes())

    table = [score("League average", league_average(split.train, split.test), split.test, known),
             score("Situation table", situation_table(split.train, split.test), split.test, known),
             score("Gradient boosting", boosted_trees(split.train, split.test), split.test, known)]
    print("  baselines scored", flush=True)

    for name, switches in ABLATIONS:
        trained = train_one(replace(base, **switches), train, settings, device,
                            validate=validate, validate_truth=split.validate.outcome)
        outcome, result = predict(trained["model"], test)
        table.append(score(f"Network: {name}", outcome, split.test, known))
        print(f"  {name}: test log loss {table[-1]['all']:.4f}", flush=True)
    # The last one trained is the full network.
    save_network(trained["model"], split.vocabulary, OUT / "evaluation")
    return dict(
        trained_through=TRAIN_THROUGH, validated_on=VALIDATE_YEAR, tested_from=VALIDATE_YEAR + 1,
        balls=dict(train=len(split.train), validate=len(split.validate), test=len(split.test)),
        known_player_share=float(known.mean()),
        curve=trained["curve"], best_epoch=trained["best_epoch"], scores=table,
        result=result_scores(result, split.test),
        calibration=dict(wicket=calibration(outcome, split.test.outcome, WICKET),
                         six=calibration(outcome, split.test.outcome, OUTCOMES.index("6"))),
        simulated_vs_real=simulated_vs_real(con, OUT / "evaluation"),
    )


def deploy(frame: pd.DataFrame, con: duckdb.DuckDBPyConnection, settings: TrainConfig, device: str) -> dict:
    """Fit the same network on every ball we hold. This is the one the site runs.

    The test above says how good the method is. A model meant for use should not throw away
    the latest seasons, least of all in a game that keeps changing.
    """
    vocabulary = build_vocabulary(frame)
    everything = encode(frame, vocabulary)
    config = ModelConfig(**vocabulary.sizes())
    trained = train_one(config, to_device(everything, device), settings, device, keep_snapshots=True)
    save_network(trained["model"], vocabulary, OUT)

    batters = batters_for_map(frame, vocabulary, con)
    players = player_file(trained["snapshots"], batters, trained["best_epoch"])
    (OUT / "players.json").write_text(json.dumps(players))
    return dict(
        trained_through=int(frame["year"].max()), balls=len(everything), vocabulary=vocabulary.sizes(),
        parameters=sum(p.numel() for p in trained["model"].parameters()), model=config.to_dict(),
        curve=trained["curve"], simulated_vs_real=simulated_vs_real(con, OUT),
    )


def run(con: duckdb.DuckDBPyConnection) -> dict:
    started = time.time()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    settings = TrainConfig()
    split, frame = load_split(con)
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"  {len(split.train):,} training balls, {len(split.test):,} test balls, on {device}", flush=True)

    card = dict(
        outcomes=OUTCOMES, inputs=NUMERIC, history=HISTORY, min_balls_for_a_vector=MIN_BALLS,
        training=vars(settings) | dict(seed=SEED, device=device),
        evaluation=evaluate(split, con, settings, device),
    )
    print("  fitting the deployed model on every ball", flush=True)
    card["deployed"] = deploy(frame, con, settings, device)
    card["seconds"] = round(time.time() - started)
    (OUT / "card.json").write_text(json.dumps(card, indent=1))
    return card
