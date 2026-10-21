"""Turns numbers into plain sentences: what a play was, what a match was about,
who a player is. Short words, short sentences, no jargon."""
from __future__ import annotations

import hashlib

from .db import q

NUMBER_WORDS = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]


# ---- small word helpers --------------------------------------------------

def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def number(n: int) -> str:
    return NUMBER_WORDS[n] if 0 <= n <= 10 else str(n)


def plural(n: int, word: str, many: str | None = None) -> str:
    return word if n == 1 else (many or word + "s")


def runs_phrase(n: int) -> str:
    return f"{number(n)} {plural(n, 'run')}"


def possessive(name: str) -> str:
    return name + ("'" if name.endswith("s") else "'s")


def percent(p: float) -> str:
    value = p * 100
    if 0 < value < 1:
        return "under 1%"
    if 99 < value < 100:
        return "over 99%"
    return f"{value:.0f}%"


def long_date(d) -> str:
    return f"{d:%B} {d.day}, {d.year}"


def pick(options: list[str], key: str) -> str:
    """A steady choice: the same match always gets the same wording."""
    return options[int(hashlib.sha256(key.encode()).hexdigest(), 16) % len(options)]


# ---- plays -----------------------------------------------------------------

CRICKET_EVENT = """
    e.seq, e.innings, e."over", e.ball, e.bat_team, e.field_team, e.runs, e.runs_bat, e.wide,
    e.noball, e.outs, e.dismissal, e.dismissed_id, e.wp1, e.wp1_post, e.wpa, e.rae,
    e.score_pre + e.runs as bat_score, e.wkts_pre + e.outs as wkts, e.target,
    e.batter_id, e.bowler_id, b.name as batter, p.name as bowler, d.name as dismissed"""


def events_sql(where: str) -> str:
    """Plays with the names needed to describe them. `where` is SQL from this codebase."""
    return f"""select e.match_id, {CRICKET_EVENT} from ck_ev e
               left join ck_players b on b.player_id = e.batter_id
               left join ck_players p on p.player_id = e.bowler_id
               left join ck_players d on d.player_id = e.dismissed_id where {where}"""


def _dismissal(e: dict) -> str:
    out, bowler, how = e["dismissed"] or e["batter"], e["bowler"], e["dismissal"]
    sentences = {
        "bowled": f"{bowler} bowled {out}",
        "lbw": f"{bowler} trapped {out} lbw",
        "caught": f"{out} was caught off {bowler}",
        "caught and bowled": f"{bowler} took a return catch to remove {out}",
        "stumped": f"{out} was stumped off {bowler}",
        "run out": f"{out} was run out",
        "hit wicket": f"{out} hit the stumps off {bowler}",
    }
    return sentences.get(how, f"{out} was out, {how}")


def describe(e: dict) -> str:
    batter, bowler, runs = e["batter"], e["bowler"], e["runs"]
    if e["outs"]:
        return _dismissal(e)
    if e["wide"]:
        return f"{bowler} bowled a wide" + (f" that cost {runs}" if runs > 1 else "")
    if e["noball"]:
        return f"{bowler} bowled a no-ball, {runs_phrase(runs)} in all"
    if e["runs_bat"] == 6:
        return f"{batter} hit {bowler} for six"
    if e["runs_bat"] == 4:
        return f"{batter} hit {bowler} for four"
    if runs == 0:
        return f"{bowler} kept {batter} scoreless"
    return f"{batter} took {number(runs)} off {bowler}"


WICKET_KINDS = {"bowled": "bowled", "lbw": "lbw", "caught": "caught", "caught and bowled": "caught",
                "stumped": "stumped", "run out": "runout"}


def kind(e: dict) -> str:
    """A short tag for each play, so the page can pick an icon and a colour for it."""
    if e["outs"]:
        return WICKET_KINDS.get(e["dismissal"], "wicket")
    if e["wide"]:
        return "wide"
    if e["noball"]:
        return "noball"
    return {6: "six", 4: "four", 0: "dot"}.get(e["runs_bat"], "runs")


def moment(e: dict) -> str:
    return f"over {e['over'] + 1} of the {ordinal(e['innings'])} innings"


# ---- one player's day ------------------------------------------------------

def _bowling_line(mine: list[dict]) -> str:
    not_the_bowlers = ("run out", "retired out", "obstructing the field")
    wickets = sum(1 for e in mine if e["outs"] and e["dismissal"] not in not_the_bowlers)
    balls = sum(1 for e in mine if not (e["wide"] or e["noball"]))
    overs = f"{balls // 6}.{balls % 6}" if balls % 6 else f"{balls // 6}"
    return f"{wickets} for {sum(e['runs'] for e in mine)} in {overs} overs"


def stat_line(role: str, events: list[dict], player_id: str) -> str:
    """What one player did in one match, as a scorer would say it."""
    if role == "bat":
        faced = [e for e in events if e["batter_id"] == player_id and not e["wide"]]
        return f"{sum(e['runs_bat'] for e in faced)} off {len(faced)} balls"
    return _bowling_line([e for e in events if e["bowler_id"] == player_id])


# ---- match stories ---------------------------------------------------------

def _loser(m: dict) -> str:
    return m["team2"] if m["winner"] == m["team1"] else m["team1"]


# Ways to say each kind of result. {w} is the winner, {l} the loser, {low} the winner's lowest chance.
HEADLINES = {
    "drawn": ["{a} and {b} share a draw", "Nothing to split {a} and {b}", "{a} and {b} end level"],
    "no result": ["{a} and {b} finish with no winner", "No result for {a} and {b}"],
    "miracle": ["{w} come back from the dead to beat {l}", "{w} steal one {l} had won",
                "From {low} to a win: {w} stun {l}"],
    "comeback": ["{w} fight back to beat {l}", "{w} turn it around against {l}", "{l} let {w} off the hook"],
    "thriller": ["{w} edge {l} in a classic", "{w} survive a wild one against {l}",
                 "{w} outlast {l} in a thriller"],
    "rout": ["{w} cruise past {l}", "{w} never let {l} in", "{w} run away from {l}"],
    "in control": ["{w} stay in front to beat {l}", "{w} hold off {l}", "{w} keep {l} at arm's length"],
    "plain win": ["{w} beat {l}", "{w} get past {l}", "{w} too good for {l}"],
}


def _kind_of_result(m: dict) -> str:
    """Which story the numbers tell. `winner_low` is the winner's lowest win chance in the match."""
    if not m["winner"]:
        return "drawn" if m.get("note") == "draw" else "no result"
    low = m.get("winner_low") if m.get("winner_low") is not None else 0.5
    thrill = m.get("thrill") if m.get("thrill") is not None else 0.5
    if low < 0.03:
        return "miracle"
    if low < 0.12:
        return "comeback"
    if thrill > 0.93:
        return "thriller"
    if thrill < 0.25 and low > 0.4:
        return "rout"
    if low > 0.35:
        return "in control"
    return "plain win"


def headline(m: dict) -> str:
    """A headline for a match. The same match always gets the same one."""
    wording = pick(HEADLINES[_kind_of_result(m)], m["match_id"])
    low = m.get("winner_low")
    return wording.format(
        a=m["team1"], b=m["team2"], w=m["winner"], l=_loser(m) if m["winner"] else None,
        low=percent(low) if low is not None else "")


def result_line(m: dict) -> str:
    where = f" at {m['venue']}" if m.get("venue") else ""
    when = f" on {long_date(m['date'])}"
    if not m["winner"]:
        ending = "ended in a draw" if m.get("note") == "draw" else "finished without a winner"
        return f"{m['team1']} and {m['team2']} {ending}{where}{when}."
    winner, loser = m["winner"], _loser(m)
    if (m.get("note") or "").startswith("by "):
        return f"{winner} beat {loser} {m['note']}{where}{when}."
    scores = (m["score1"], m["score2"]) if winner == m["team1"] else (m["score2"], m["score1"])
    return f"{winner} beat {loser} {scores[0]:.0f}–{scores[1]:.0f}{where}{when}."


def _wildness_rank(sport: str, m: dict) -> dict:
    """Where this match ranks among its league's games that year, by total swing."""
    scope = [sport, m["league"], m["year"]]
    return q("""select count(*) + 1 as place,
                       (select count(*) from matches where sport = ? and league = ? and year = ?) as of
                from matches x join match_stats s using (sport, match_id)
                where x.sport = ? and x.league = ? and x.year = ? and s.excitement > ?""",
             [*scope, *scope, m["excitement"]])[0]


def _swing_sentences(sport: str, m: dict) -> tuple[str, str]:
    """How often the favourite changed, and how wild the match was for its league and year."""
    changes = m["lead_changes"]
    if changes:
        changed = f"The favourite changed {changes} {plural(changes, 'time')}."
    else:
        changed = "The favourite never changed."
    rank = _wildness_rank(sport, m)
    place = "the wildest" if rank["place"] == 1 else f"the {ordinal(rank['place'])} wildest"
    ranked = (f"By how far the win chance swung, it was {place} of "
              f"{rank['of']:,} {m['league']} games in {m['year']}.")
    return changed, ranked


def match_story(sport: str, m: dict, events: list[dict], players: list[dict]) -> dict:
    """A headline, a one-line summary and a few paragraphs.

    `events` carry their sentence in `text`. `players` are ordered by win chance added,
    best first, and the leaders carry a stat `line`.
    """
    winner, low = m["winner"], m.get("winner_low")
    comeback = ""
    if winner and low is not None and low < 0.12:
        comeback = f"At their lowest point {winner} had a {percent(low)} chance."

    turn = max(events, key=lambda e: abs(e["wp1_post"] - e["wp1"]))
    star = players[0] if players else None
    paragraphs = [" ".join(filter(None, [result_line(m), comeback]))]
    paragraphs.append(
        f"The biggest moment came in {moment(turn)}. {turn['text']}. "
        f"That moved {possessive(m['team1'])} chance of winning "
        f"from {percent(turn['wp1'])} to {percent(turn['wp1_post'])}.")
    if star:
        paragraphs.append(f"{star['name']} did the most to decide it: {star['line']}. "
                          f"That was worth {star['wpa'] * 100:+.0f} points of win chance.")
    changed = ""
    if m.get("lead_changes") is not None and m.get("thrill") is not None:
        changed, ranked = _swing_sentences(sport, m)
        paragraphs.append(f"{changed} {ranked}")

    star_line = f"{star['name']}: {star['line']}." if star else ""
    return dict(
        headline=headline(m),
        standfirst=" ".join(filter(None, [comeback, star_line, changed])),
        paragraphs=paragraphs,
        turning=dict(seq=turn["seq"], text=turn["text"]),
    )


# ---- people and teams -------------------------------------------------------

def _main_league(spec, player_id: str) -> dict | None:
    """The league a player has played most in, with the totals there."""
    rows = q(f"""select league, arg_max(team, year) as team,
                        min(year) as first_year, max(year) as last_year,
                        sum({spec.opps}) as n, sum(rae) as rae
                 from {spec.table} where player_id = ?
                 group by league order by n desc limit 1""", [player_id])
    return rows[0] if rows else None


def _value_rank(spec, league: str, rae: float) -> dict:
    return q(f"""select count(*) + 1 as place,
                        (select count(distinct player_id) from {spec.table} where league = ?) as of
                 from (select player_id, sum(rae) as total from {spec.table} where league = ? group by 1)
                 where total > ?""", [league, league, rae])[0]


def player_lede(player_id: str, name: str, role: str, spec, profile: dict | None) -> list[str]:
    """Two or three sentences that say who a player is and how good."""
    main = _main_league(spec, player_id)
    if not main:
        return []
    verb = "bats" if role == "bat" else "bowls"
    first, last = main["first_year"], main["last_year"]
    span = str(first) if first == last else f"{first} to {last}"
    sentences = [f"{name} {verb} for {main['team']}. "
                 f"Our {main['league']} record of this player runs from {span}."]

    rank = _value_rank(spec, main["league"], main["rae"])
    direction = "more" if main["rae"] >= 0 else "fewer"
    place = "the best" if rank["place"] == 1 else ordinal(rank["place"])
    sentences.append(
        f"That record is worth {abs(main['rae']):,.0f} runs {direction} than an average player "
        f"in the same spots. It ranks {place} of {rank['of']:,} in {main['league']}.")

    if profile and profile.get("dims"):
        skills = sorted(profile["dims"], key=lambda d: d["pct"])
        weakest, best = skills[0], skills[-1]
        sentences.append(
            f"Best skill: {best['label'].lower()}, ahead of {min(best['pct'], 99):.0f}% of players. "
            f"Weakest: {weakest['label'].lower()}, ahead of {weakest['pct']:.0f}%.")
    return sentences


def team_lede(team: dict) -> list[str]:
    """`team` is the team page payload: rank, seasons, current state and best players."""
    season, now = team["seasons"][0], team.get("now") or {}
    wins, losses = season["w"], season["l"]
    sentences = [
        f"{team['team']} rank {ordinal(team['rank'])} of {team['of']} active sides in {team['pool']} "
        f"by our rating. Their latest season: {wins} {plural(wins, 'win')}, "
        f"{losses} {plural(losses, 'loss', 'losses')}."]
    if now.get("form") is not None:
        sentences.append(f"They have won {round(now['form'] * 10)} of their last 10.")
    leaders = team["best"]["bat"][:1] + team["best"]["bowl"][:1]
    if leaders:
        top = max(leaders, key=lambda r: r["rae"])
        sentences.append(f"{top['name']} has added the most for them in {team['year']}: "
                         f"{top['rae']:+.0f} runs against average.")
    return sentences
