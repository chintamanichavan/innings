"""Matchups, impact and the question box: the style reader, the question reader, and the
slice engine checked against the season tables it must agree with."""
import pytest
from fastapi.testclient import TestClient

from innings.balls import batting_hand, bowling_type
from innings.config import DB_PATH
from innings.ingest.styles import field, plain


@pytest.mark.parametrize("words, expected", [
    ("Right-arm fast", "right-pace"),
    ("Right-arm fast-medium", "right-pace"),
    ("Left-arm medium-fast", "left-pace"),
    ("Right-arm off break", "off-spin"),
    ("Right-arm off spin", "off-spin"),
    ("Right-arm leg break googly", "leg-spin"),
    ("Leg spin", "leg-spin"),
    ("Slow left-arm orthodox", "left-orthodox"),
    ("Left-arm unorthodox spin", "left-wrist"),
    ("Left-arm wrist spin", "left-wrist"),
    ("Right-arm off break, Right-arm leg break", "off-spin"),     # the first one listed
    ("Right-arm medium / Right-arm off spin", "right-pace"),
    ("", None),
    ("None", None),
])
def test_bowling_styles_read_as_types(words, expected):
    assert bowling_type(words) == expected


def test_batting_hand():
    assert batting_hand("Left-handed") == "L"
    assert batting_hand("Right-handed") == "R"
    assert batting_hand("") is None


def test_infobox_field_drops_markup():
    text = """{{Infobox cricketer
| batting = Right-handed
| bowling = Right-arm [[Fast bowling|fast]]<ref>{{cite web|url=x}}</ref>
| role = [[Bowler (cricket)|Bowler]]
}}"""
    assert plain(field(text, "bowling")) == "Right-arm fast"
    assert plain(field(text, "batting")) == "Right-handed"
    assert field(text, "fielding") == ""
    assert plain("[[Leg spin]]<br/>[[Googly]]<!-- note -->") == "Leg spin, Googly"


def test_infobox_lists_are_read_in_order():
    listed = "{{ubl|Right-arm [[Off spin|off break]], [[Leg spin|leg break]]}}"
    assert plain(listed) == "Right-arm off break, leg break"
    assert bowling_type(plain("{{ubl|Right-arm medium|Right-arm [[off break]]}}")) == "right-pace"


built = pytest.mark.skipif(not DB_PATH.exists(), reason="database not built")


@pytest.fixture(scope="module")
def client():
    from innings.web.app import app
    return TestClient(app)


def get(client, path, **params):
    reply = client.get(path, params=params)
    assert reply.status_code == 200, reply.text
    return reply.json()


@built
def test_question_reader_finds_each_part():
    from innings.web.ask import read
    reading = read("Bumrah death overs IPL 2024")
    s = reading.slice
    assert (s.role, s.league, s.phase, s.first, s.last) == ("bowl", "IPL", "death", 2024, 2024)
    assert s.bowler and not reading.unknown
    s = read("Kohli vs leg spin since 2020").slice
    assert (s.role, s.type, s.first, s.last, s.by) == ("bat", "leg-spin", 2020, 0, "year")
    s = read("Kohli v Bumrah").slice
    assert s.batter and s.bowler and s.role == "bat"
    s = read("spinners in the powerplay BBL").slice
    assert (s.role, s.family, s.phase, s.by) == ("bowl", "spin", "powerplay", "player")
    s = read("MI vs CSK 2020-2023").slice
    assert (s.team, s.opponent, s.first, s.last) == ("Mumbai Indians", "Chennai Super Kings", 2020, 2023)
    assert read("most sixes IPL 2025").sort == "sixes"
    assert read("florp zibble").unknown == ["florp", "zibble"]


@built
@pytest.mark.parametrize("role, table", [("bat", "ck_bat"), ("bowl", "ck_bowl")])
def test_a_player_slice_adds_up_to_the_season_table(client, role, table):
    """A whole-career slice must give the same balls, runs and RAE as the season table."""
    from innings.web.db import q
    player = q(f"""select player_id from {table} where league = 'IPL'
                   group by 1 order by sum(balls) desc limit 1""")
    pid = player[0]["player_id"]
    who = "batter" if role == "bat" else "bowler"
    total = get(client, "/api/slice", role=role, **{who: pid}, league="IPL")["total"]
    season = q(f"select sum(balls) as balls, sum(runs) as runs, sum(rae) as rae from {table} "
               "where player_id = ? and league = 'IPL'", [pid])[0]
    assert total["balls"] == season["balls"]
    assert total["runs"] == season["runs"]
    assert total["rae"] == pytest.approx(season["rae"], abs=1e-6)


@built
def test_split_rows_never_exceed_the_total(client):
    answer = get(client, "/api/slice", role="bat", league="IPL", first=2024, last=2024, by="phase")
    assert [row["key"] for row in answer["rows"]] == ["powerplay", "middle", "death"]
    assert sum(row["balls"] for row in answer["rows"]) == answer["total"]["balls"]
    typed = get(client, "/api/slice", role="bat", league="IPL", first=2024, last=2024, by="type")
    assert sum(row["balls"] for row in typed["rows"]) <= typed["total"]["balls"]


@built
def test_expected_wickets_average_out(client):
    """Across every ball, wickets above average must come to nothing."""
    total = get(client, "/api/slice", role="bowl")["total"]
    assert total["waa"] == pytest.approx(0, abs=1e-6)


@built
def test_bad_slices_are_refused(client):
    assert client.get("/api/slice", params={"phase": "tea"}).status_code == 400
    assert client.get("/api/slice", params={"by": "mood"}).status_code == 400
    assert client.get("/api/slice", params={"first": "x"}).status_code == 400


@built
def test_ask_answers_and_reports(client):
    reply = get(client, "/api/ask", q="best death bowlers IPL 2025")
    assert reply["answer"]["rows"] and reply["sort"] == "rae"
    assert get(client, "/api/ask", q="")["answer"] is None
