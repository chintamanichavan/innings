"""The command line: load data, build the models and tables, serve the site, keep it fresh."""
from __future__ import annotations

import argparse
import time
from collections.abc import Callable

import duckdb

from . import aggregates, balls, insights
from .config import PORT
from .db import connect, rebuild
from .ingest import cricsheet, styles
from .models import cricket, predict

# Each step reads what the ones before it wrote, so the order matters.
BUILD_STEPS: list[tuple[str, Callable]] = [
    ("cricket values", cricket.build),
    ("season tables", aggregates.build),
    ("match prediction", predict.build),
    ("insights", insights.build),
    ("ball table", balls.build),
]


def _timed(name: str, step: Callable, *args) -> None:
    started = time.time()
    print(f"{name} ...", flush=True)
    step(*args)
    print(f"{name} done in {time.time() - started:.0f}s", flush=True)


def ingest(con: duckdb.DuckDBPyConnection, refresh: bool) -> None:
    _timed("cricket data", cricsheet.ingest, con, refresh)
    _timed("playing styles", styles.ingest, con, refresh)


def build(con: duckdb.DuckDBPyConnection) -> None:
    for name, step in BUILD_STEPS:
        _timed(name, step, con)


def refresh_forever(hours: float) -> None:
    """Rebuild from fresh downloads on a timer. A failed run leaves the old database in place."""
    while True:
        time.sleep(hours * 3600)
        try:
            with rebuild(fresh=True) as con:
                ingest(con, refresh=True)
                build(con)
        except Exception as error:
            print(f"refresh failed: {error}", flush=True)


def train() -> None:
    """Train the neural network and write it under data/nn/. Needs the `train` extra."""
    from .db import connect
    from .nn import train as nn_train  # imported here: PyTorch is not installed where the site runs
    con = connect(read_only=True)
    _timed("neural network", nn_train.run, con)
    con.close()


def serve(host: str, port: int) -> None:
    import uvicorn  # imported here so that building the data does not need the web stack loaded
    uvicorn.run("innings.web.app:app", host=host, port=port)


def stream(args: argparse.Namespace) -> None:
    """The live stream: a bowler sends balls into Kafka, scorers add the win chance."""
    from .stream import bench, bowler, scorer  # imported here: only the stream needs Kafka
    if args.part == "bowl":
        bowler.run(args.pace, args.grounds)
    elif args.part == "score":
        scorer.run(args.group, args.source, args.sink)
    else:
        result = bench.run(args.scorers, args.matches)
        bench.record(result)
        print(f"{result['balls']:,} balls through {result['scorers']} scorer(s) in {result['seconds']}s: "
              f"{result['per_second']:,} a second. Furthest from the build: {result['worst_difference']:.1e}")


def season(args: argparse.Namespace) -> None:
    """One IPL season played again many times on the graphics card, streamed into a data lake."""
    from .season import lake, run, tally  # imported here: this needs PyTorch and Kafka
    if args.part == "run":
        report = run.run(args.year, args.seasons)
        counts = report["counts"]
        print(f"{report['made']['balls']:,} balls in {report['seconds']}s: {report['balls_per_second']:,} "
              f"a second. Counted by the simulator {counts['simulator']:,}, the tally {counts['tally']:,} "
              f"and the lake {counts['lake']:,}.")
    elif args.part == "lake":
        lake.main(args.topic, [args.partition], run.season_of(args.year)[0])
    else:
        tally.run(args.topic, run.season_of(args.year)[0], args.seasons)


def market() -> None:
    """Score the model's chances against the betting market's on Big Bash matches."""
    from .market import compare
    with connect(read_only=True) as con:
        result = compare.run(con)
    counts, pooled, betting = result["matches"], result["pooled"], result["betting"]
    print(f"{counts['scored']} matches scored of {counts['priced']} priced. Brier, all moments: "
          f"model {pooled['brier_model']:.4f}, market {pooled['brier_market']:.4f}. "
          f"{betting['bets']} bets returned {betting['return_per_unit']:+.3f} a unit. "
          f"Written to {compare.REPORT}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="innings")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, summary in (("all", "load data, then build"), ("ingest", "load data only")):
        command = commands.add_parser(name, help=summary)
        command.add_argument("--refresh", action="store_true", help="download the data again")
    commands.add_parser("build", help="rebuild models and tables from data already loaded")
    commands.add_parser("train", help="train the neural network (needs the train extra and a GPU)")
    command = commands.add_parser("refresh", help="rebuild from fresh data on a timer")
    command.add_argument("--every", type=float, default=12, help="hours between runs")
    command = commands.add_parser("stream", help="the live stream through Kafka")
    parts = command.add_subparsers(dest="part", required=True)
    part = parts.add_parser("bowl", help="replay past matches into Kafka as if live")
    part.add_argument("--pace", type=float, default=0.8, help="seconds between balls")
    part.add_argument("--grounds", type=int, default=3, help="matches playing at once")
    part = parts.add_parser("score", help="read balls, keep the score, add the win chance")
    part.add_argument("--group", default="scorers", help="scorers in one group share the matches")
    part.add_argument("--source", default="balls", help="topic to read")
    part.add_argument("--sink", default="scored", help="topic to write")
    part = parts.add_parser("bench", help="measure balls per second, and check every answer")
    part.add_argument("--scorers", type=int, default=1)
    part.add_argument("--matches", type=int, default=2000)
    command = commands.add_parser("season", help="play a season many times, into a data lake")
    parts = command.add_subparsers(dest="part", required=True)
    part = parts.add_parser("run", help="the whole job (needs the train extra, a GPU and Kafka)")
    part.add_argument("--year", type=int, default=2026)
    part.add_argument("--seasons", type=int, default=100_000)
    part = parts.add_parser("lake", help="one lake writer; started by `run`")
    part.add_argument("topic")
    part.add_argument("partition", type=int)
    part.add_argument("year", type=int)
    part = parts.add_parser("tally", help="the running count; started by `run`")
    part.add_argument("topic")
    part.add_argument("year", type=int)
    part.add_argument("seasons", type=int)
    commands.add_parser("market", help="compare the model's chances with the betting market's")
    command = commands.add_parser("serve", help="run the web site")
    command.add_argument("--host", default="127.0.0.1")
    command.add_argument("--port", type=int, default=PORT)
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "all":
        with rebuild(fresh=True) as con:
            ingest(con, args.refresh)
            build(con)
    elif args.command == "ingest":
        with rebuild(fresh=False) as con:
            ingest(con, args.refresh)
    elif args.command == "build":
        with rebuild(fresh=False) as con:
            build(con)
    elif args.command == "train":
        train()
    elif args.command == "refresh":
        refresh_forever(args.every)
    elif args.command == "season":
        season(args)
    elif args.command == "stream":
        stream(args)
    elif args.command == "market":
        market()
    elif args.command == "serve":
        serve(args.host, args.port)


if __name__ == "__main__":
    main()
