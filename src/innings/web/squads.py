"""A team's season as a fan follows it: the squad by role, and the league's points table."""
from __future__ import annotations

from collections import defaultdict

from ..config import INTERNATIONAL
from .db import per_database, q

ROLES = ["Batters", "Wicketkeepers", "All-rounders", "Bowlers"]
BOWLS = 6      # balls a match, on average: a player bowling an over a game is a bowler
BATS = 8       # balls faced a match: a bowler also facing this much is an all-rounder
ALL_OUT = 10


def _role(player: dict) -> str:
    """Read off what the player did, as no source lists roles. A keeper made a stumping for the side
    in the last three years: only a keeper can."""
    if player["keeper"]:
        return "Wicketkeepers"
    bowls = player["bowled"] / player["matches"] >= BOWLS
    bats = player["faced"] / player["matches"] >= BATS
    if bowls:
        return "All-rounders" if bats else "Bowlers"
    return "Batters"


@per_database(max_entries=200)
def squad(pool: str, team: str, year: int) -> list[dict]:
    """Everyone the team picked in this season, grouped by role, most-picked first."""
    players = q("""
        with games as (select match_id from matches
                       where sport = 'ck' and pool = ? and year = ? and (team1 = ? or team2 = ?)),
        named as (select l.player_id, count(*) as matches from ck_lineups l join games using (match_id)
                  where l.team = ? group by 1),
        batting as (select e.batter_id as player_id, sum(e.runs_bat) as runs,
                           sum(case when e.wide then 0 else 1 end) as faced
                    from ck_events e join games using (match_id) where e.bat_team = ? group by 1),
        bowling as (select e.bowler_id as player_id, sum(e.bowler_wicket::int) as wickets,
                           sum(case when e.wide or e.noball then 0 else 1 end) as bowled
                    from ck_events e join games using (match_id) where e.field_team = ? group by 1),
        keepers as (select distinct e.fielder_id as player_id
                    from ck_events e join ck_matches m using (match_id)
                    where e.dismissal = 'stumped' and m.year > ? - 3 and e.field_team = ?)
        select n.player_id, p.name, n.matches, coalesce(b.runs, 0) as runs,
               coalesce(b.faced, 0) as faced, coalesce(w.wickets, 0) as wickets,
               coalesce(w.bowled, 0) as bowled, k.player_id is not null as keeper
        from named n join ck_players p using (player_id)
        left join batting b using (player_id) left join bowling w using (player_id)
        left join keepers k using (player_id)
        order by n.matches desc, runs + 20 * wickets desc""",
                [pool, year, team, team, team, team, team, year, team])
    for player in players:
        player["role"] = _role(player)
    return sorted(players, key=lambda player: ROLES.index(player["role"]))


def is_league(pool: str) -> bool:
    """A franchise league has a points table. Internationals are a stream of series, so they do not."""
    return not pool.startswith(INTERNATIONAL)


def _overs_used(innings: dict, full: int) -> int:
    """Balls an innings counts for in net run rate: all of them if the side was bowled out."""
    return full if innings["wickets"] >= ALL_OUT else innings["balls"]


@per_database(max_entries=100)
def points_table(pool: str, year: int) -> list[dict]:
    """The league stage as the league prints it: P W L NR Pts NRR, two points a win, one for no result.

    Net run rate is runs an over scored less runs an over conceded. A side bowled out is
    counted as having faced its full overs, as the rules say.
    """
    games = q("""select m.match_id, m.team1, m.team2, m.winner, c.max_balls from matches m
                 join ck_matches c using (match_id)
                 where m.sport = 'ck' and m.pool = ? and m.year = ? and c.stage is null""", [pool, year])
    innings = q("""select e.match_id, e.bat_team as team, sum(e.runs) as runs, sum(e.outs) as wickets,
                          sum(case when e.wide or e.noball then 0 else 1 end) as balls
                   from ck_events e where e.match_id in (select unnest(?)) group by all""",
                [[game["match_id"] for game in games]])
    batted = {(row["match_id"], row["team"]): row for row in innings}
    rows: dict[str, dict] = defaultdict(lambda: dict(played=0, won=0, lost=0, no_result=0, points=0,
                                                     scored=0, faced=0, conceded=0, bowled=0))
    for game in games:
        sides = (game["team1"], game["team2"])
        for team, other in (sides, sides[::-1]):
            row = rows[team]
            row["played"] += 1
            if game["winner"] is None:
                row["no_result"] += 1
                row["points"] += 1
                continue
            won = game["winner"] == team
            row["won" if won else "lost"] += 1
            row["points"] += 2 * won
            ours, theirs = batted.get((game["match_id"], team)), batted.get((game["match_id"], other))
            if ours and theirs:
                row["scored"] += ours["runs"]
                row["faced"] += _overs_used(ours, game["max_balls"])
                row["conceded"] += theirs["runs"]
                row["bowled"] += _overs_used(theirs, game["max_balls"])
    table = []
    for team, row in rows.items():
        rate_for = 6 * row["scored"] / row["faced"] if row["faced"] else 0
        rate_against = 6 * row["conceded"] / row["bowled"] if row["bowled"] else 0
        shown = {key: row[key] for key in ("played", "won", "lost", "no_result", "points")}
        table.append({"team": team, **shown, "net_run_rate": round(rate_for - rate_against, 3)})
    return sorted(table, key=lambda row: (-row["points"], -row["net_run_rate"]))
