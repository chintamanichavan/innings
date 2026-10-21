"""Team ratings, matchup forecasts, team and venue pages, and the model tables."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ...config import FULL_MEMBERS, INTERNATIONAL
from ...models.predict import FEATURES
from .. import matches, stories, teams
from ..db import q
from ..specs import known_sport, spec_for

router = APIRouter(prefix="/api", dependencies=[Depends(known_sport)])

ELO_POINTS = 400   # enough to draw a rating history


@router.get("/ratings")
def ratings(sport: str, pool: str, everyone: bool = False):
    rows = teams.active(sport, pool)
    # Ratings cannot compare nations that never meet, so internationals show full members only.
    members_only = pool.startswith(INTERNATIONAL) and not everyone
    if members_only:
        rows = [r for r in rows if r["team"].removesuffix(" (W)") in FULL_MEMBERS]
    return dict(rows=rows, full_members_only=members_only)


@router.get("/predict")
def predict(sport: str, pool: str, a: str, b: str):
    """Team a's chance against team b, batting first and batting second."""
    state = {row["team"]: row for row in teams.states(sport, pool) if row["team"] in (a, b)}
    if a not in state or b not in state or a == b:
        raise HTTPException(400, "pick two different teams from the same league")
    first = teams.chance_first(sport, state[a], state[b])
    second = 1 - teams.chance_first(sport, state[b], state[a])
    return dict(a=state[a], b=state[b], a_first=first, a_second=second, neutral=(first + second) / 2)


@router.get("/eval")
def evaluation(sport: str):
    """How the forecast did on seasons it never trained on."""
    calibration = q("""
        select model, floor(p * 10) / 10 + 0.05 as bucket, avg(p) as predicted, avg(y) as actual,
               count(*) as n
        from (select 'full' as model, p_full as p, y from predictions where sport = ?
              union all select 'elo', p_elo, y from predictions where sport = ?)
        group by all having count(*) >= 20 order by model, bucket""", [sport, sport])
    overall = q("""select model, sum(n) as n, sum(accuracy * n) / sum(n) as accuracy,
                          sum(log_loss * n) / sum(n) as log_loss, sum(brier * n) / sum(n) as brier
                   from pred_eval where sport = ? group by model order by log_loss""", [sport])
    return dict(
        by_year=q("select * from pred_eval where sport = ? order by year, model", [sport]),
        overall=overall,
        calibration=calibration,
        weights=q("select feature, coef from pred_model where sport = ? and feature <> 'intercept'", [sport]),
        features=FEATURES,
    )


@router.get("/models")
def models(sport: str, league: str = ""):
    """The state-value tables behind the numbers, for the How it works page."""
    competition = league.removesuffix(" (W)") or "IPL"
    fmt = competition if competition in ("ODI", "Test") else "T20"
    return dict(
        metrics=q("select * from model_metrics where sport = 'ck' and model = ?", [f"win_prob:{fmt}"]),
        league=competition, fmt=fmt,
        er=q("""select balls_left, wkts, er from ck_er_grid where competition = ?
                order by wkts, balls_left desc""", [competition]),
    )


def _rating_history(sport: str, pool: str, team: str) -> list[dict]:
    history = q("""select date, elo from elo_history where sport = ? and pool = ? and team = ?
                   order by date""", [sport, pool, team])
    step = max(1, len(history) // ELO_POINTS)
    return history[::step] + history[-1:]


def _best_players(sport: str, pool: str, team: str, year: int) -> dict[str, list[dict]]:
    """The team's leaders by runs above average, in this pool's leagues, for one year."""
    best = {}
    for role in ("bat", "bowl"):
        spec = spec_for(sport, role)
        best[role] = q(f"""
            select t.player_id, p.name, sum(t.{spec.opps}) as n, sum(t.rae) as rae, sum(t.wpa) as wpa
            from {spec.table} t join players p on p.sport = ? and p.player_id = t.player_id
            where t.team = ? and t.year = ? and t.league = ?
            group by all order by rae desc limit 8""", [sport, team, year, pool])
    return best


@router.get("/team")
def team_page(sport: str, pool: str, team: str):
    seasons = q("""select year, league, g, w, l, rf, ra from team_season
                   where sport = ? and pool = ? and team = ? order by year desc, g desc""",
                [sport, pool, team])
    if not seasons:
        raise HTTPException(404, "no such team")
    table = teams.active(sport, pool)
    rank = next((place for place, row in enumerate(table, start=1) if row["team"] == team), None)
    year = seasons[0]["year"]
    played = "m.sport = ? and m.pool = ? and (m.team1 = ? or m.team2 = ?)"
    page = dict(
        team=team, pool=pool, year=year, seasons=seasons,
        now=next((row for row in teams.states(sport, pool) if row["team"] == team), None),
        rank=rank, of=len(table),
        elo=_rating_history(sport, pool, team),
        best=_best_players(sport, pool, team, year),
        games=matches.cards(played, [sport, pool, team, team], "m.date desc", 12),
        classics=matches.cards("m.sport = ? and m.pool = ? and m.winner = ?", [sport, pool, team],
                               "s.excitement desc", 6),
    )
    page["lede"] = stories.team_lede(page)
    return page


@router.get("/venues")
def venues(sport: str):
    return q("""select venue, league, n, first, last, avg1, avg2, first_win, excitement
                from venues where sport = ? and n >= 15 order by n desc limit 200""", [sport])


@router.get("/venue")
def venue(sport: str, name: str):
    found = q("select * from venues where sport = ? and venue = ?", [sport, name])
    if not found:
        raise HTTPException(404, "no such venue")
    by_year = q("""
        select year, count(*) as n, avg(score1) as avg1, avg(score2) as avg2,
               avg(case when winner = team1 then 1.0 when winner = team2 then 0.0 end) as first_win
        from matches where sport = ? and venue = ? group by year order by year""", [sport, name])
    classics = matches.cards("m.sport = ? and m.venue = ? and m.winner is not null", [sport, name],
                             "s.thrill desc", 9)
    return dict(venue=found[0], by_year=by_year, classics=classics)
