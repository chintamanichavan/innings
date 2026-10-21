"""The small pieces of logic, tested without the database."""
import pytest

from innings.models.ratings import PARAMS, PlayerRatings, TeamRatings, expected_score
from innings.web import stories


def test_elo_expected_score():
    assert expected_score(1500, 1500, 0) == pytest.approx(0.5)
    assert expected_score(1500, 1500, 24) < 0.5            # the second-named side is at home
    assert expected_score(1900, 1500, 0) == pytest.approx(10 / 11)


def test_team_ratings_move_toward_the_result_and_sum_to_zero():
    teams = TeamRatings(PARAMS["ck"])
    teams.record("India", "Australia", first_won=1.0)
    assert teams.elo["India"] > 1500 > teams.elo["Australia"]
    assert teams.elo["India"] + teams.elo["Australia"] == pytest.approx(3000)
    assert teams.form("India") == 0.5                      # one game is too few to call form


def test_new_year_pulls_a_rating_back_toward_average():
    teams = TeamRatings(PARAMS["ck"])
    teams.elo["India"] = 1700
    teams.start_of_match("India", 2025)
    assert teams.elo["India"] == 1700                      # first sighting: nothing to carry over
    teams.start_of_match("India", 2026)
    assert teams.elo["India"] == pytest.approx(1500 + 0.85 * 200)


def test_player_rating_starts_average_and_fades_with_time():
    players = PlayerRatings(PARAMS["ck"])
    assert players.batting("kohli", day=0) == (0.0, 0.0)
    players.add("kohli", 0, bat_chances=150, bat_value=30, bowl_chances=0, bowl_value=0)
    rate, chances = players.batting("kohli", day=0)
    assert rate == pytest.approx(30 / (150 + 150)) and chances == 150
    _, later = players.batting("kohli", day=540)           # one half-life on
    assert later == pytest.approx(75)


@pytest.mark.parametrize("n,expected", [(1, "1st"), (2, "2nd"), (3, "3rd"), (4, "4th"), (11, "11th"),
                                        (12, "12th"), (13, "13th"), (21, "21st"), (33, "33rd"),
                                        (101, "101st"), (111, "111th")])
def test_ordinal(n, expected):
    assert stories.ordinal(n) == expected


def test_small_words():
    assert stories.possessive("India") == "India's" and stories.possessive("Dodgers") == "Dodgers'"
    assert stories.runs_phrase(1) == "one run" and stories.runs_phrase(3) == "three runs"
    assert stories.percent(0.004) == "under 1%" and stories.percent(0.996) == "over 99%"
    assert stories.percent(0.5) == "50%"


def test_headline_follows_the_kind_of_match():
    base = dict(match_id="x", team1="India", team2="Australia", winner="India", note=None)
    assert "India" in stories.headline(dict(base, winner_low=0.5, thrill=0.5))
    assert stories._kind_of_result(dict(base, winner_low=0.01, thrill=0.9)) == "miracle"
    assert stories._kind_of_result(dict(base, winner_low=0.45, thrill=0.1)) == "rout"
    assert stories._kind_of_result(dict(base, winner=None, note="draw")) == "drawn"
    # The same match always gets the same wording.
    match = dict(base, winner_low=0.08, thrill=0.6)
    assert stories.headline(match) == stories.headline(dict(match))


def test_cricket_plays_read_as_sentences():
    ball = dict(batter="Kohli", bowler="Starc", runs=6, runs_bat=6, wide=False, noball=False,
                outs=0, dismissal=None, dismissed=None)
    assert stories.describe(ball) == "Kohli hit Starc for six"
    assert stories.describe(dict(ball, runs=0, runs_bat=0)) == "Starc kept Kohli scoreless"
    out = dict(ball, runs=0, runs_bat=0, outs=1, dismissal="lbw", dismissed="Kohli")
    assert stories.describe(out) == "Starc trapped Kohli lbw"
    assert stories.kind(out) == "lbw" and stories.kind(ball) == "six"


def test_overs_are_written_the_cricket_way():
    from innings.web.scorecard import overs_text

    assert overs_text(120) == "20"
    assert overs_text(119) == "19.5"
    assert overs_text(0) == "0"


def test_dismissals_read_as_a_scorecard_writes_them():
    from innings.web.scorecard import how_out

    assert how_out("caught", "Smith", "Starc") == "c Smith b Starc"
    assert how_out("caught and bowled", None, "Starc") == "c & b Starc"
    assert how_out("lbw", None, "Bumrah") == "lbw b Bumrah"
    assert how_out("run out", "Jadeja", "Bumrah") == "run out (Jadeja)"
    assert how_out("run out", None, "Bumrah") == "run out"
    assert how_out("retired out", None, "Bumrah") == "retired out"
