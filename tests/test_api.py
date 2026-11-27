"""Smoke tests against the built database. Run `innings all` first."""
import pytest
from fastapi.testclient import TestClient

from innings.config import DB_PATH
from innings.web.app import app

pytestmark = pytest.mark.skipif(not DB_PATH.exists(), reason="database not built")
client = TestClient(app)


def get(path, **params):
    r = client.get(path, params=params)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.parametrize("role", ["bat", "bowl"])
def test_leaders_and_player(role):
    sport = "ck"
    d = get("/api/leaders", sport=sport, role=role, league="IPL", year=2024)
    assert len(d["rows"]) > 20
    top = d["rows"][0]
    assert top["rae"] > 0
    p = get(f"/api/player/{sport}/{top['player_id']}")
    assert role in p["roles"]


def test_known_leaders():
    ck = get("/api/leaders", sport="ck", role="bowl", league="IPL", year=2024)
    assert ck["rows"][0]["name"] == "Jasprit Bumrah"


def test_match_win_probability():
    ms = get("/api/matches", sport="ck", league="IPL", limit=5)
    d = get(f"/api/match/ck/{ms[0]['match_id']}")
    assert "bridge" not in d
    ev, m = d["events"], d["match"]
    assert all(0 <= e["wp1"] <= 1 for e in ev)
    # The curve must end on the real result.
    assert ev[-1]["wp1_post"] == (1.0 if m["winner"] == m["team1"] else 0.0)
    # Each side's win probability added sums to what it gained over the match.
    gain = sum(e["wpa"] if e["bat_team"] == m["team1"] else -e["wpa"] for e in ev)
    assert gain == pytest.approx(ev[-1]["wp1_post"] - ev[0]["wp1"], abs=1e-6)


def test_run_values_average_to_zero():
    ck = get("/api/models", sport="ck", league="IPL")
    full = next(r for r in ck["er"] if r["balls_left"] == 120 and r["wkts"] == 0)
    assert 150 < full["er"] < 230


@pytest.mark.parametrize("pool", ["IPL", "T20I"])
def test_predict(pool):
    sport = "ck"
    teams = [r["team"] for r in get("/api/ratings", sport=sport, pool=pool)["rows"]]
    assert len(teams) >= 8
    p = get("/api/predict", sport=sport, pool=pool, a=teams[0], b=teams[-1])
    assert 0.5 < p["neutral"] < 1
    back = get("/api/predict", sport=sport, pool=pool, a=teams[-1], b=teams[0])
    assert p["neutral"] + back["neutral"] == pytest.approx(1)


def test_prediction_beats_coin_flip():
    overall = {r["model"]: r for r in get("/api/eval", sport="ck")["overall"]}
    assert overall["full"]["log_loss"] < overall["elo"]["log_loss"] < overall["base rate"]["log_loss"]


def test_search_matchup_meta():
    assert get("/api/search", sport="ck", q="kohli")[0]["name"] == "Virat Kohli"
    assert get("/api/meta")["leagues"]
    k = get("/api/search", sport="ck", q="kohli")[0]["player_id"]
    b = get("/api/search", sport="ck", q="bumrah")[0]["player_id"]
    assert get("/api/matchup", sport="ck", batter=k, bowler=b)["rows"][0]["balls"] > 50


def test_fan_feed_and_records():
    sport = "ck"
    h = get("/api/home", sport=sport)
    assert h["lead"] and h["recent"] and h["hot_bat"] and h["top_play"]
    assert 0 <= h["lead"]["match"]["thrill"] <= 1
    # The front page gets only what its chart draws, not every play in words.
    assert set(h["lead"]["events"][0]) == {"seq", "period", "half", "wp1", "wp1_post"}
    assert h["forecast"]["n"] > 4000 and set(h["forecast"]) == {"n", "right"}
    for kind in ("thrillers", "comebacks", "plays", "bat_games", "bowl_games"):
        assert len(get("/api/records", sport=sport, kind=kind)) == 50
    low = get("/api/records", sport=sport, kind="comebacks")[0]
    assert low["winner_low"] < 0.05


def test_player_extra():
    pid = get("/api/search", sport="ck", q="kohli")[0]["player_id"]
    x = get(f"/api/player-extra/ck/{pid}")
    assert not {"bridge", "twin"} & set(x)
    dims = x["profile"]["bat"]["dims"]
    assert len(dims) == 5 and all(0 <= d["pct"] <= 100 for d in dims)
    assert x["splits"] and x["log"] and len(x["series"]) > 10
def test_team_and_venue():
    t = get("/api/team", sport="ck", pool="IPL", team="Mumbai Indians")
    assert t["seasons"] and len(t["elo"]) > 50 and t["best"]["bat"] and "twin" not in t
    v = get("/api/venues", sport="ck")[0]
    assert get("/api/venue", sport="ck", name=v["venue"])["classics"]


def test_games():
    sport = "ck"
    d = get("/api/game/daily", sport=sport, shown=6, day="2026-10-07")
    assert len(d["hints"]) == d["total"] == 6
    assert len(get("/api/game/daily", sport=sport, shown=1, day="2026-10-07")["hints"]) == 1
    wrong = get("/api/game/guess", sport=sport, player_id="nobody", day="2026-10-07")
    assert wrong == {"correct": False, "answer": None}
    answer = get("/api/game/guess", sport=sport, player_id="nobody", day="2026-10-07", last=True)["answer"]
    assert get("/api/game/guess", sport=sport, player_id=answer["player_id"], day="2026-10-07")["correct"]
    assert len(get("/api/game/higher-lower", sport=sport)["cards"]) == 14
    assert len(get("/api/game/pick", sport=sport)) == 10


def test_find():
    f = get("/api/find", term="mumbai")
    assert f["teams"][0]["team"] == "Mumbai Indians"


@pytest.mark.parametrize("league,top", [("ODI", "Virat Kohli"), ("Test", "Joe Root")])
def test_international_formats(league, top):
    d = get("/api/leaders", sport="ck", role="bat", league=league)
    assert d["rows"][0]["name"] == top
    assert get("/api/ratings", sport="ck", pool=league)["rows"]


def test_test_match_draw_and_four_innings():
    # 2019 Ashes: Lord's was drawn, Headingley was won by one wicket.
    draw = get("/api/match/ck/1152847")
    assert draw["match"]["winner"] is None and draw["match"]["note"] == "draw"
    assert draw["events"][-1]["wp1_post"] == 0.5
    won = get("/api/match/ck/1152848")
    assert {e["period"] for e in won["events"]} == {1, 2, 3, 4}
    assert won["match"]["winner"] == "England" and won["match"]["winner_low"] < 0.1


def test_match_story_reads_as_sentences():
    d = get("/api/match/ck/1152848")
    st = d["story"]
    assert st["headline"] and len(st["paragraphs"]) >= 3
    assert all(p.endswith(".") for p in st["paragraphs"])
    # No scorer codes leak into the words.
    assert not any("/" in e["text"] or "(" in e["text"] for e in d["events"])
    assert any(e["seq"] == st["turning"]["seq"] for e in d["events"])


def test_the_server_answers_only_under_api():
    """Pages are the website's job now. This server holds data and models, nothing else."""
    assert client.get("/api/nope").status_code == 404
    assert client.get("/cricket").status_code == 404


def test_onboarding_and_my_teams():
    teams = get("/api/onboarding")
    assert {t["pool"] for t in teams} >= {"IPL", "T20I"} and {t["sport"] for t in teams} == {"ck"}
    mine = get("/api/my", teams="ck|India;ck|Australia")
    assert [m["team"] for m in mine] == ["India", "Australia"] and mine[0]["match"]["headline"]


def test_forecast_points_rule():
    from innings.web.forecasts import points
    assert points(0.5, True) == points(0.5, False) == 0
    assert points(1.0, True) == 25 and points(1.0, False) == -75
    assert points(0.7, True) == pytest.approx(16) and points(0.7, False) == pytest.approx(-24)


def test_forecast_record_beats_a_coin():
    f = get("/api/forecasts", sport="ck")
    r = f["record"]
    assert r["n"] > 4000 and r["right"] / r["n"] > 0.55 and r["per_call"] > 0
    assert sum(x["n"] for x in f["by_league"]) == r["n"]
    assert all(not m["right"] and m["points"] < 0 for m in f["misses"])
    assert f["series"][-1]["value"] == pytest.approx(r["points"])
    assert set(f) == {"record", "by_league", "by_year", "series", "recent", "misses"}


@pytest.mark.parametrize("path", [
    "/api/home?sport=bb", "/api/records?sport=bb", "/api/leaders?sport=bb", "/api/search?sport=bb",
    "/api/matches?sport=bb", "/api/ratings?sport=bb&pool=MLB", "/api/eval?sport=bb", "/api/models?sport=bb",
    "/api/venues?sport=bb", "/api/forecasts?sport=bb", "/api/game/higher-lower?sport=bb",
    "/api/game/pick?sport=bb", "/api/player/bb/x", "/api/player-extra/bb/x", "/api/match/bb/x",
])
def test_unknown_sport_is_a_404(path):
    assert client.get(path).status_code == 404


@pytest.mark.parametrize("path", ["/api/bridge/table", "/api/bridge/translate", "/api/live",
                                  "/api/starters", "/api/twins", "/api/forecasts/calls"])
def test_baseball_endpoints_are_gone(path):
    assert client.get(path).status_code == 404


def test_ordinals():
    from innings.web.stories import ordinal
    assert [ordinal(n) for n in (1, 2, 3, 4, 11, 12, 13, 21, 22, 33, 101, 111)] == [
        "1st", "2nd", "3rd", "4th", "11th", "12th", "13th", "21st", "22nd", "33rd", "101st", "111th"]


def test_scorecard_adds_up():
    match = get("/api/matches", sport="ck", league="IPL", limit=1)[0]
    card = get(f"/api/scorecard/{match['match_id']}")
    assert len(card["innings"]) == 2
    for innings in card["innings"]:
        off_the_bat = sum(line["runs"] for line in innings["batting"])
        assert off_the_bat + innings["extras"]["total"] == innings["runs"]
        assert sum(line["out"] for line in innings["batting"]) == innings["wickets"]
        assert len(innings["fall_of_wickets"]) == innings["wickets"]
        assert sum(stand["runs"] for stand in innings["partnerships"]) == innings["runs"]
        assert innings["by_over"][-1]["score"] == innings["runs"]
        # What the bowlers gave away, plus byes, is the total.
        assert sum(line["runs"] for line in innings["bowling"]) + innings["extras"]["byes"] == innings["runs"]
        assert len(innings["batting"]) + len(innings["did_not_bat"]) >= 11
    first, second = card["innings"]
    assert {first["team"], second["team"]} == {match["team1"], match["team2"]}
    assert first["runs"] == match["score1"] and second["runs"] == match["score2"]


def test_players_most_alike_are_other_players_in_the_same_format():
    kohli = get("/api/find", term="Virat Kohli")["players"][0]["player_id"]
    extra = get(f"/api/player-extra/ck/{kohli}")
    alike = extra["alike"]
    assert len(alike) == 5 and kohli not in {row["player_id"] for row in alike}
    assert {row["fmt"] for row in alike} == {extra["profile"][extra["role"]]["fmt"]}
    assert [row["match"] for row in alike] == sorted((row["match"] for row in alike), reverse=True)


def test_scores_read_the_cricket_way():
    final = get("/api/match/ck/1535465")["match"]                  # IPL 2026 final
    assert final["line1"] == "155/8 (20 ov)" and final["line2"] == "161/5 (18 ov)"
    assert final["result"] == "Royal Challengers Bengaluru won by 5 wickets (12 balls left)"
    lords = get("/api/match/ck/1152847")["match"]                  # 2019 Ashes, Lord's: a draw
    assert lords["line1"] == "258 & 258/5d" and lords["result"] == "Match drawn"


def test_career_summary_by_format():
    kohli = get("/api/find", term="Virat Kohli")["players"][0]["player_id"]
    career = get(f"/api/career/{kohli}")
    batting = {row["league"]: row for row in career["batting"]}
    assert [row["league"] for row in career["batting"]][:3] == ["Test", "ODI", "T20I"]
    odi = batting["ODI"]
    assert odi["average"] == pytest.approx(odi["runs"] / (odi["innings"] - odi["not_outs"]))
    assert odi["hundreds"] > 40 and odi["best"] == "183"
    assert len(career["recent"]) == 10


def test_team_page_has_points_table_and_squad():
    page = get("/api/team", sport="ck", pool="IPL", team="Mumbai Indians")
    table = page["table"]
    assert len(table) == 10 and all(row["played"] == 14 for row in table)
    assert all(row["points"] == 2 * row["won"] + row["no_result"] for row in table)
    assert sum(row["won"] for row in table) == sum(row["lost"] for row in table)
    assert [row["points"] for row in table] == sorted((row["points"] for row in table), reverse=True)
    roles = {player["role"] for player in page["squad"]}
    assert {"Batters", "Bowlers"} <= roles
    assert get("/api/team", sport="ck", pool="T20I", team="India")["table"] is None


def test_commentary_runs_ball_by_ball():
    overs = get("/api/commentary/1535465")["innings"][0]["overs"]
    assert len(overs) == 20 and overs[0]["balls"][0]["at"] == "0.1"
    assert overs[-1]["end"]["score"] == "155/8"
    wickets = [ball for over in overs for ball in over["balls"] if ball["wicket"]]
    assert len(wickets) == 8 and all(ball["mark"] == "W" for ball in wickets)
