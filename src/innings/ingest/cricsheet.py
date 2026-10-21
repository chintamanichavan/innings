"""Cricsheet ball-by-ball JSON (T20, ODI, Test) -> ck_matches, ck_events, ck_lineups, ck_players.

Each match is one JSON file inside a per-competition zip. A match becomes one row of
ck_matches and one row of ck_events per ball, each ball carrying the state of the game
just before it was bowled.
"""
from __future__ import annotations

import csv
import json
import zipfile
from dataclasses import dataclass

import duckdb
import pandas as pd

from ..config import CK_ARCHIVES, CK_BALLS, RAW
from .download import fetch

ARCHIVE_URL = "https://cricsheet.org/downloads/{code}_json.zip"
NAMES_URL = "https://cricsheet.org/register/names.csv"

# Franchises that changed name. Old -> current, so a club's history stays in one piece.
TEAM_ALIASES = {
    "Royal Challengers Bangalore": "Royal Challengers Bengaluru",
    "Delhi Daredevils": "Delhi Capitals",
    "Kings XI Punjab": "Punjab Kings",
    "Rising Pune Supergiants": "Rising Pune Supergiant",
    "Melbourne Renegades Men": "Melbourne Renegades",
    "St Lucia Zouks": "St Lucia Kings",
    "St Lucia Stars": "St Lucia Kings",
    "Barbados Tridents": "Barbados Royals",
    "Trinidad & Tobago Red Steel": "Trinbago Knight Riders",
}

# Ways a batter leaves that are not a wicket, and wickets that are not the bowler's.
NOT_A_WICKET = {"retired hurt", "retired not out"}
NOT_THE_BOWLERS = NOT_A_WICKET | {"run out", "retired out", "obstructing the field", "timed out"}

MATCH_COLUMNS = [
    "match_id", "date", "year", "season", "competition", "format", "max_balls", "event", "stage",
    "gender", "team_type", "venue", "city", "team1", "team2", "toss_winner", "toss_decision",
    "winner", "result", "method", "note",
    # score is a side's runs across all its innings; wkts and balls describe its first innings
    "score1", "wkts1", "balls1", "score2", "wkts2", "balls2",
]
EVENT_COLUMNS = [
    "match_id", "seq", "innings", "over", "ball", "bat_team", "field_team",
    "batter_id", "non_striker_id", "bowler_id",
    "runs_bat", "extras", "runs", "wide", "noball", "byes", "outs", "bowler_wicket",
    "dismissed_id", "dismissal", "fielder_id", "score_pre", "wkts_pre", "balls_left_pre", "target",
    "lead_pre", "inn_balls_pre", "match_balls_pre",
]
# Whole-number columns that can be empty, which pandas would otherwise turn into floats.
NULLABLE_INTEGERS = ("max_balls", "balls_left_pre", "target", "score2", "wkts2", "balls2")


@dataclass
class InningsTotal:
    runs: int
    wickets: int
    legal_balls: int


def _first_fielder(wicket: dict) -> str | None:
    """The catcher, stumper or thrower named for a wicket, if the scorer named one."""
    named = [fielder["name"] for fielder in wicket.get("fielders", []) if "name" in fielder]
    return named[0] if named else None


def _overs_to_balls(overs) -> int:
    """Cricket writes 17.3 overs for 17 overs and 3 balls."""
    whole = int(overs)
    return whole * 6 + round((float(overs) - whole) * 10)


def _team_name(name: str, info: dict) -> str:
    """The current name of a side. A women's national side is marked, as it shares its nation's name."""
    name = TEAM_ALIASES.get(name, name)
    if info.get("team_type") == "international" and info.get("gender") == "female":
        name += " (W)"
    return name


def _result_note(outcome: dict, winner) -> str | None:
    """The result as a scorecard states it: 'by 5 wickets', 'by an innings and 20 runs', 'draw'."""
    if not winner:
        return outcome.get("result")
    if outcome.get("method"):
        return outcome["method"]
    margin = outcome.get("by", {})
    lead_in = "by an innings and " if "innings" in margin else "by "
    for unit in ("runs", "wickets"):
        if unit in margin:
            count = margin[unit]
            return f"{lead_in}{count} {unit[:-1] if count == 1 else unit}"
    return outcome.get("result")


def _target(innings_number: int, limited: bool, declared: dict, batting_total: int,
            fielding_total: int) -> int | None:
    """Runs the batting side needs to win, when the innings is a chase."""
    if limited and innings_number == 2:
        return declared.get("runs", fielding_total + 1)
    if not limited and innings_number == 4:
        return fielding_total - batting_total + 1
    return None


def _parse_match(match_id: str, competition: str, fmt: str, data: dict):
    """One match file -> (match row, ball rows, lineup rows, {player id: name}), or None to skip it."""
    info = data["info"]
    full_innings = CK_BALLS[fmt]
    wrong_length = full_innings and info.get("overs") != full_innings // 6
    if info.get("balls_per_over", 6) != 6 or wrong_length:
        return None
    innings_list = [inn for inn in data.get("innings", []) if not inn.get("super_over") and inn.get("overs")]
    if full_innings:
        innings_list = innings_list[:2]
    if not innings_list:
        return None

    player_ids = info.get("registry", {}).get("people", {})
    name_of = {raw: _team_name(raw, info) for raw in info["teams"]}
    match_runs = dict.fromkeys(info["teams"], 0)   # each side's runs across all its innings so far
    balls: list[tuple] = []
    totals: list[InningsTotal] = []
    seq = match_balls = 0

    for number, innings in enumerate(innings_list, start=1):
        batting = innings["team"]
        fielding = next(side for side in info["teams"] if side != batting)
        declared = innings.get("target", {})
        # A rain-reduced chase is told how many overs it has.
        shortened = number == 2 and "overs" in declared
        ball_limit = _overs_to_balls(declared["overs"]) if shortened else full_innings
        target = _target(number, bool(full_innings), declared, match_runs[batting], match_runs[fielding])
        lead_at_start = match_runs[batting] - match_runs[fielding]
        runs = wickets = legal_balls = 0

        for over in innings["overs"]:
            for ball_in_over, ball in enumerate(over["deliveries"], start=1):
                extras = ball.get("extras", {})
                wide, no_ball = "wides" in extras, "noballs" in extras
                outs = [w for w in ball.get("wickets", []) if w["kind"] not in NOT_A_WICKET]
                scored = ball["runs"]
                seq += 1
                balls.append((
                    match_id, seq, number, over["over"], ball_in_over, name_of[batting], name_of[fielding],
                    player_ids.get(ball["batter"]), player_ids.get(ball["non_striker"]),
                    player_ids.get(ball["bowler"]),
                    scored["batter"], scored["extras"], scored["total"], wide, no_ball,
                    extras.get("byes", 0) + extras.get("legbyes", 0),
                    len(outs), any(w["kind"] not in NOT_THE_BOWLERS for w in outs),
                    player_ids.get(outs[0]["player_out"]) if outs else None,
                    outs[0]["kind"] if outs else None,
                    player_ids.get(_first_fielder(outs[0])) if outs else None,
                    # the state before this ball
                    runs, wickets, ball_limit - legal_balls if ball_limit else None, target,
                    lead_at_start + runs, legal_balls, match_balls,
                ))
                legal = not (wide or no_ball)
                runs += scored["total"]
                wickets += len(outs)
                legal_balls += legal
                match_balls += legal
        match_runs[batting] += runs
        totals.append(InningsTotal(runs, wickets, legal_balls))

    first_side = innings_list[0]["team"]
    second_side = next(side for side in info["teams"] if side != first_side)
    second_batted = len(totals) > 1
    outcome = info.get("outcome", {})
    winner = outcome.get("winner") or outcome.get("eliminator") or outcome.get("bowl_out")
    toss = info.get("toss", {})
    date = info["dates"][0]
    match = (
        match_id, date, int(date[:4]), str(info.get("season", date[:4])), competition, fmt, full_innings,
        info.get("event", {}).get("name"), info.get("event", {}).get("stage"),
        info.get("gender"), info.get("team_type"), info.get("venue"), info.get("city"),
        name_of[first_side], name_of[second_side],
        name_of.get(toss.get("winner")), toss.get("decision"),
        name_of.get(winner), outcome.get("result", "win" if winner else None), outcome.get("method"),
        _result_note(outcome, winner),
        match_runs[first_side], totals[0].wickets, totals[0].legal_balls,
        match_runs[second_side] if second_batted else None,
        totals[1].wickets if second_batted else None,
        totals[1].legal_balls if second_batted else None,
    )
    lineups = [(match_id, name_of[side], player_ids[player])
               for side, players in info.get("players", {}).items()
               for player in players if player_ids.get(player)]
    people = {player_id: name for name, player_id in player_ids.items()}
    return match, balls, lineups, people


def _full_names(scorecard_names: dict[str, str], refresh: bool) -> dict[str, str]:
    """Scorecards say 'V Kohli'. The Cricsheet register lists other spellings of a name.

    Where one of them spells out the first name, use it. It must share the surname and the
    first initial, because the register also holds unrelated names for some players.
    """
    best: dict[str, str] = {}
    path = fetch(NAMES_URL, RAW / "cricsheet" / "names.csv", refresh)
    with open(path, newline="", encoding="utf-8") as file:
        for player_id, name in csv.reader(file):
            on_card = scorecard_names.get(player_id, "").split()
            words = name.split()
            if len(on_card) < 2 or len(words) < 2 or not on_card[0].isupper() or "(" in name:
                continue
            same_person = words[-1].lower() == on_card[-1].lower() and words[0][0].upper() == on_card[0][0]
            spelled_out = len(words[0]) >= 3 and not words[0].isupper()
            if same_person and spelled_out and len(name) > len(best.get(player_id, "")):
                best[player_id] = name
    return best


def _store(con: duckdb.DuckDBPyConnection, table: str, columns: list[str], rows: list, first: bool) -> None:
    """Create the table from `rows`, or append to it."""
    frame = pd.DataFrame(rows, columns=columns)
    if "date" in columns:
        frame["date"] = pd.to_datetime(frame["date"]).dt.date
    for column in NULLABLE_INTEGERS:
        if column in frame:
            frame[column] = frame[column].astype("Int64")
    con.register("_rows", frame)
    con.execute(f"create or replace table {table} as select * from _rows" if first
                else f"insert into {table} select * from _rows")
    con.unregister("_rows")


def ingest(con: duckdb.DuckDBPyConnection, refresh: bool = False) -> None:
    names: dict[str, str] = {}
    loaded: set[str] = set()   # a match can appear in more than one archive
    for index, (code, (competition, fmt)) in enumerate(CK_ARCHIVES.items()):
        matches, balls, lineups = [], [], []
        archive = fetch(ARCHIVE_URL.format(code=code), RAW / "cricsheet" / f"{code}_json.zip", refresh)
        with zipfile.ZipFile(archive) as bundle:
            for filename in bundle.namelist():
                match_id = filename.removesuffix(".json")
                if not filename.endswith(".json") or match_id in loaded:
                    continue
                loaded.add(match_id)
                parsed = _parse_match(match_id, competition, fmt, json.loads(bundle.read(filename)))
                if parsed is None:
                    continue
                match, match_balls, match_lineups, people = parsed
                matches.append(match)
                balls.extend(match_balls)
                lineups.extend(match_lineups)
                names.update(people)
        # One archive at a time keeps memory flat: there are five million balls in all.
        _store(con, "ck_matches", MATCH_COLUMNS, matches, first=index == 0)
        _store(con, "ck_events", EVENT_COLUMNS, balls, first=index == 0)
        _store(con, "ck_lineups", ["match_id", "team", "player_id"], lineups, first=index == 0)
        print(f"  cricsheet {code}: {len(matches)} matches", flush=True)
    names.update(_full_names(names, refresh))
    _store(con, "ck_players", ["player_id", "name"], sorted(names.items()), first=True)
