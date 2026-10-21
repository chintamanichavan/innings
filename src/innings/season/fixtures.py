"""One real IPL season as a simulator needs it: who played whom, where, and with which players.

Every league match keeps its real ground, its real batting orders and its real bowling plan:
the same bowler bowls the same over as on the day. Only the balls are played again.
"""
from __future__ import annotations

from dataclasses import dataclass

import duckdb
import numpy as np

from ..nn.features import UNKNOWN

ELEVEN = 11
OVERS = 20
MOST_OVERS = 4           # one bowler may bowl a fifth of a T20 innings
PLAYOFFS = ["Qualifier 1", "Eliminator", "Qualifier 2", "Final"]


@dataclass
class Season:
    year: int
    teams: list[str]                 # a team's number is its place here
    people: list[tuple[str, str]]    # (player id, name); a person's number is their place here
    sides: np.ndarray                # [league match, 2] team numbers
    venues: np.ndarray               # [league match] the network's ground ids
    order: np.ndarray                # [league match, 2, 11] people, in batting order
    plan: np.ndarray                 # [league match, 2, 20] people: who bowls each over
    usual_order: np.ndarray          # [team, 11] the order from a team's last league match
    usual_plan: np.ndarray           # [team, 20]
    playoff_venues: np.ndarray       # [4] grounds of Qualifier 1, Eliminator, Qualifier 2, Final
    batter_ids: np.ndarray           # [person] the network's id for each person as a batter
    bowler_ids: np.ndarray           # [person] and as a bowler
    real: dict                       # what really happened, to set beside the simulations

    @property
    def matches(self) -> int:
        return len(self.sides) + len(PLAYOFFS)


def _batting_orders(con, year: int) -> dict[tuple[str, str], list[str]]:
    """For each (match, team): its players in the order they came in, then those who did not bat."""
    came_in = con.execute("""
        with seen as (
            select match_id, bat_team as team, batter_id as player_id, seq * 2 as at from ck_events
            union all
            select match_id, bat_team, non_striker_id, seq * 2 + 1 from ck_events)
        select s.match_id, s.team, s.player_id, min(s.at) as first_seen
        from seen s join ck_matches m using (match_id)
        where m.competition = 'IPL' and m.year = ? and s.player_id is not null
        group by all order by s.match_id, s.team, first_seen""", [year]).fetchall()
    orders: dict[tuple[str, str], list[str]] = {}
    for match_id, team, player_id, _ in came_in:
        orders.setdefault((match_id, team), []).append(player_id)

    # Those named in the side who never got in go after, most-used batters of the season first.
    named = con.execute("""
        select l.match_id, l.team, l.player_id,
               (select count(*) from ck_events e join ck_matches m2 using (match_id)
                where e.batter_id = l.player_id and m2.competition = 'IPL' and m2.year = ?) as faced
        from ck_lineups l join ck_matches m using (match_id)
        where m.competition = 'IPL' and m.year = ? order by l.match_id, l.team, faced desc, l.player_id
        """, [year, year]).fetchall()
    for match_id, team, player_id, _ in named:
        order = orders.setdefault((match_id, team), [])
        if player_id not in order:
            order.append(player_id)
    return {key: order[:ELEVEN] for key, order in orders.items() if len(order) >= ELEVEN}


def _bowling_plans(con, year: int) -> dict[tuple[str, str], list[str]]:
    """For each (match, team): who bowled each of the 20 overs.

    An innings that ended early leaves overs unbowled. They go to the bowlers already used
    that day, in the order they first bowled, none going past four overs.
    """
    bowled = con.execute("""
        select e.match_id, e.field_team, e."over", arg_min(e.bowler_id, e.seq) as bowler
        from ck_events e join ck_matches m using (match_id)
        where m.competition = 'IPL' and m.year = ? and e."over" < ?
        group by all order by e.match_id, e.field_team, e."over" """, [year, OVERS]).fetchall()
    by_side: dict[tuple[str, str], dict[int, str]] = {}
    for match_id, team, over, bowler in bowled:
        by_side.setdefault((match_id, team), {})[over] = bowler

    plans = {}
    for key, overs in by_side.items():
        used = list(dict.fromkeys(overs.values()))
        count = {bowler: list(overs.values()).count(bowler) for bowler in used}
        plan = []
        for over in range(OVERS):
            if over not in overs:
                spare = [bowler for bowler in used if count[bowler] < MOST_OVERS] or used
                overs[over] = min(spare, key=lambda bowler: count[bowler])
                count[overs[over]] += 1
            plan.append(overs[over])
        plans[key] = plan
    return plans


def _what_happened(con, year: int, teams: list[str]) -> dict:
    wins = dict(con.execute("""select winner, count(*) from ck_matches
                               where competition = 'IPL' and year = ? and stage is null and winner is not null
                               group by 1""", [year]).fetchall())
    stages = dict(con.execute("""select stage, winner from ck_matches
                                 where competition = 'IPL' and year = ? and stage is not null""",
                              [year]).fetchall())
    knockouts = con.execute("""select team1, team2 from ck_matches
                               where competition = 'IPL' and year = ? and stage is not null""", [year])
    in_playoffs = {team for sides in knockouts.fetchall() for team in sides}
    return {"champion": stages.get("Final"), "league_wins": [wins.get(team, 0) for team in teams],
            "playoffs": sorted(in_playoffs)}


def load(con: duckdb.DuckDBPyConnection, year: int, vocabulary: dict) -> Season:
    league = con.execute("""
        select match_id, team1, team2, venue from ck_matches
        where competition = 'IPL' and year = ? and stage is null
        order by date, match_id""", [year]).fetchall()
    knockouts = dict(con.execute("""select stage, venue from ck_matches
                                    where competition = 'IPL' and year = ? and stage is not null""",
                                 [year]).fetchall())
    teams = sorted({team for _, home, away, _ in league for team in (home, away)})
    orders, plans = _batting_orders(con, year), _bowling_plans(con, year)

    person_number: dict[str, int] = {}

    def numbers(player_ids: list[str]) -> list[int]:
        return [person_number.setdefault(player_id, len(person_number)) for player_id in player_ids]

    # A washed-out match has no order or plan of its own: it borrows the team's latest one.
    latest_order: dict[str, list[int]] = {}
    latest_plan: dict[str, list[int]] = {}
    pending = []
    order = np.zeros((len(league), 2, ELEVEN), dtype=np.int64)
    plan = np.zeros((len(league), 2, OVERS), dtype=np.int64)
    for match, (match_id, home, away, _) in enumerate(league):
        for side, team in enumerate((home, away)):
            if (match_id, team) in orders and (match_id, team) in plans:
                latest_order[team] = numbers(orders[match_id, team])
                latest_plan[team] = numbers(plans[match_id, team])
            if team in latest_order:
                order[match, side], plan[match, side] = latest_order[team], latest_plan[team]
            else:
                pending.append((match, side, team))   # washed out before the team had played at all
    for match, side, team in pending:
        order[match, side], plan[match, side] = latest_order[team], latest_plan[team]

    names = dict(con.execute("select player_id, name from ck_players").fetchall())
    people = [(player_id, names.get(player_id, player_id)) for player_id in person_number]
    venue_id = vocabulary["venues"]
    return Season(
        year=year, teams=teams, people=people,
        sides=np.array([[teams.index(home), teams.index(away)] for _, home, away, _ in league]),
        venues=np.array([venue_id.get(venue, UNKNOWN) for *_, venue in league]),
        order=order, plan=plan,
        usual_order=np.array([latest_order[team] for team in teams]),
        usual_plan=np.array([latest_plan[team] for team in teams]),
        playoff_venues=np.array([venue_id.get(knockouts.get(stage), UNKNOWN) for stage in PLAYOFFS]),
        batter_ids=np.array([vocabulary["batters"].get(player_id, UNKNOWN) for player_id, _ in people]),
        bowler_ids=np.array([vocabulary["bowlers"].get(player_id, UNKNOWN) for player_id, _ in people]),
        real=_what_happened(con, year, teams),
    )
