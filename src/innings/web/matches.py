"""Matches: the cards that link to them, the biggest plays, and the full match page."""
from __future__ import annotations

from fastapi import HTTPException

from ..config import FULL_MEMBERS, INTERNATIONAL
from . import stories
from .db import per_database, q

COLUMNS = """m.sport, m.match_id, m.date, m.year, m.league, m.fmt, m.venue, m.team1, m.team2,
             m.score1, m.score2, m.winner, m.note, s.excitement, s.thrill, s.winner_low, s.lead_changes"""
SOURCE = "from matches m join match_stats s using (sport, match_id)"

_members = ", ".join(f"'{t}'" for t in sorted(FULL_MEMBERS))
_international = " or ".join(f"m.league like '{name}%'" for name in INTERNATIONAL)
# Matches a general fan cares about: franchise cricket, and internationals between two
# full member nations.
MAJOR = (f"(not ({_international}) or ("
         f"replace(m.team1, ' (W)', '') in ({_members}) and replace(m.team2, ' (W)', '') in ({_members})))")


def cards(where: str, params: list, order: str, limit: int, offset: int = 0) -> list[dict]:
    """Matches for story cards, each with its headline.

    `where` and `order` are SQL written in this codebase, never text from a request.
    Values from a request go in `params`.
    """
    rows = q(f"select {COLUMNS} {SOURCE} where {where} order by {order} limit ? offset ?",
             [*params, limit, offset])
    for row in rows:
        row["headline"] = stories.headline(row)
    return rows


def plays(where: str, params: list, limit: int, offset: int = 0) -> list[dict]:
    """The biggest single plays, largest swing first, each described in a sentence."""
    rows = q(f"""
        select t.sport, t.match_id, t.seq, t.moment, t.what, t.wp1, t.wp1_post, t.bat_team,
               t.batter_id, t.bowler_id, m.date, m.league, m.team1, m.team2
        from top_plays t join matches m using (sport, match_id)
        where {where} order by abs(t.wp1_post - t.wp1) desc limit ? offset ?""",
             [*params, limit, offset])
    if rows:
        keys = ", ".join(f"('{r['match_id']}', {int(r['seq'])})" for r in rows)
        events = q(stories.events_sql(f"(e.match_id, e.seq) in ({keys})"))
        by_key = {(e["match_id"], e["seq"]): e for e in events}
        for r in rows:
            event = by_key.get((r["match_id"], r["seq"]))
            r["text"] = stories.describe(event) if event else r["what"]
    return rows


def _page_event(e: dict) -> dict:
    """One play, cut down to what the page draws and says."""
    return dict(period=e["innings"], half=e["innings"] - 1, at=f"{e['over']}.{e['ball']}",
                score=f"{e['bat_team']} {e['bat_score']}/{e['wkts']}",
                seq=e["seq"], bat_team=e["bat_team"], text=e["text"], kind=e["kind"],
                wp1=e["wp1"], wp1_post=e["wp1_post"], wpa=e["wpa"])


def _players(sport: str, match_id: str, events: list[dict]) -> list[dict]:
    """Everyone who played, by win chance added. The top and bottom few get a stat line."""
    rows = q("""select pm.player_id, p.name, pm.bat_w + pm.bowl_w as wpa, pm.bat_v + pm.bowl_v as rae,
                       pm.bat_w, pm.bowl_w
                from player_match pm join players p using (sport, player_id)
                where pm.sport = ? and pm.match_id = ? order by wpa desc""", [sport, match_id])
    for row in rows[:3] + rows[-2:]:
        role = "bat" if abs(row["bat_w"]) >= abs(row["bowl_w"]) else "bowl"
        row["line"] = stories.stat_line(role, events, row["player_id"])
    return rows


@per_database(max_entries=300)
def payload(sport: str, match_id: str) -> dict:
    """Everything the match page needs: the score, every play in words, and the story."""
    found = q("""select m.*, s.excitement, s.thrill, s.winner_low, s.lead_changes
                  from matches m left join match_stats s using (sport, match_id)
                  where m.sport = ? and m.match_id = ?""", [sport, match_id])
    if not found:
        raise HTTPException(404, "no such match")
    match = found[0]
    events = q(stories.events_sql("e.match_id = ?") + " order by e.seq", [match_id])
    if not events:
        raise HTTPException(404, "no plays recorded for this match")
    for e in events:
        e["text"] = stories.describe(e)
        e["kind"] = stories.kind(e)
    players = _players(sport, match_id, events)
    call = q("select p_full as p1 from predictions where sport = ? and match_id = ?", [sport, match_id])
    return dict(
        match=match,
        events=[_page_event(e) for e in events],
        players=players,
        story=stories.match_story(sport, match, events, players),
        call=call[0] if call else None,
    )


def summary(sport: str, match_id: str) -> dict:
    """A match for the front page: the story and just enough of each play to draw the chart."""
    full = payload(sport, match_id)
    keep = ("seq", "period", "half", "wp1", "wp1_post")
    return dict(match=full["match"], story=full["story"],
                events=[{k: e[k] for k in keep} for e in full["events"]])
