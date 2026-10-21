"""The comparison with the betting market: prices into chances, moments into game states,
and the scores, on small cases worked by hand."""
import datetime as dt

import numpy as np
import pandas as pd
import pytest

from innings.market import betfair, compare, moments


def test_a_tight_price_becomes_the_middle_of_its_two_chances():
    back, lay = pd.Series([2.0]), pd.Series([2.04])
    assert betfair.chance(back, lay).iloc[0] == pytest.approx((0.5 + 1 / 2.04) / 2)


def test_a_missing_or_wide_price_is_not_used():
    back, lay = pd.Series([2.0, np.nan, 220.0, 3.0]), pd.Series([2.02, 2.0, 180.0, 4.0])
    chances = betfair.chance(back, lay)
    assert chances.iloc[0] > 0
    assert chances.iloc[1:].isna().all()   # missing; back above lay by a fifth; lay too far above


def test_prices_reads_one_match_and_scales_the_two_sides_to_one(tmp_path):
    columns = {"EVENT_DATE": ["2024-12-15 00:00:00.000 Z"] * 2, "MARKET_ID": [7, 7],
               "RUNNER_NAME": ["Perth Scorchers", "Melbourne Stars"], "IS_WINNER": [1, 0]}
    for moment in betfair.MOMENTS:
        columns[f"BEST_BACK_{moment}"] = [1.9, 2.1]
        columns[f"BEST_LAY_{moment}"] = [1.92, 2.12]
    for name in betfair.SEASONS.values():
        pd.DataFrame(columns).to_csv(tmp_path / f"{name}_Match_Odds.csv", index=False)
    match = betfair.prices(tmp_path).iloc[0]
    assert match["side_a"] == "Perth Scorchers" and match["winner"] == "Perth Scorchers"
    assert match["date"] == dt.date(2024, 12, 15)
    a, b = (1 / 1.9 + 1 / 1.92) / 2, (1 / 2.1 + 1 / 2.12) / 2
    assert match["FIRST_BALL"] == pytest.approx(a / (a + b))
    assert match["FIRST_BALL_back_b"] == 2.1


def balls_of_one_match(first_innings_balls: int, second_innings_balls: int) -> pd.DataFrame:
    rows = ([(1, 120 - i) for i in range(first_innings_balls)]
            + [(2, 120 - i) for i in range(second_innings_balls)])
    return pd.DataFrame({"match_id": "m", "seq": range(len(rows)),
                         "innings": [r[0] for r in rows], "balls_left_pre": [r[1] for r in rows]})


def test_after_four_overs_is_the_first_ball_of_the_fifth():
    states = moments.states(balls_of_one_match(120, 120)).set_index("moment")
    assert states.loc["FIRST_INN_FOUR_OV", "balls_left_pre"] == 96
    assert states.loc["FIRST_INN_CONCLUSION", "innings"] == 2
    assert states.loc["FIRST_INN_CONCLUSION", "balls_left_pre"] == 120


def test_a_moment_the_match_never_reached_has_no_state():
    states = moments.states(balls_of_one_match(120, 50))   # chase won inside nine overs
    assert "SECOND_INN_SIX_OV" in set(states["moment"])
    assert "SECOND_INN_TEN_OV" not in set(states["moment"])


def test_brier_and_log_loss_of_a_coin_flip():
    p, y = np.array([0.5, 0.5]), np.array([1, 0])
    assert compare.brier(p, y) == pytest.approx(0.25)
    assert compare.log_loss(p, y) == pytest.approx(np.log(2))


def test_calibration_error_is_zero_when_chances_come_true_as_often_as_said():
    p = np.array([0.25] * 4 + [0.75] * 4)
    y = np.array([1, 0, 0, 0, 1, 1, 1, 0])
    assert compare.calibration(p, y)["error"] == pytest.approx(0.0)
    assert compare.calibration(np.full(4, 0.75), np.zeros(4))["error"] == pytest.approx(0.75)


def test_a_bet_is_placed_only_on_a_big_enough_edge_and_paid_at_the_back_price():
    rows = pd.DataFrame({"match_id": ["m1", "m2", "m3"], "moment": "FIRST_BALL",
                         "p_model": [0.60, 0.52, 0.30], "p_market": [0.50, 0.50, 0.50],
                         "back_a": [2.0, 2.0, 2.0], "back_b": [2.0, 2.0, 1.9], "y": [1, 1, 1]})
    placed = compare.bets(rows)
    assert list(placed["match_id"]) == ["m1", "m3"]          # m2's edge is too small
    assert list(placed["profit"]) == [1.0, -1.0]             # m1 backs A and wins; m3 backs B and loses


def test_matches_are_joined_on_both_sides_and_a_date_a_day_either_way():
    dates = [dt.date(2024, 12, 16), dt.date(2024, 12, 20)]
    matches = pd.DataFrame({"match_id": ["x", "y"], "date": dates,
                            "season": "2024/25", "team1": ["Sydney Sixers", "Sydney Sixers"],
                            "team2": ["Perth Scorchers", "Brisbane Heat"], "winner": "Sydney Sixers"})
    market = pd.DataFrame({"season": ["2024/25"], "date": [dt.date(2024, 12, 15)],
                           "side_a": ["Perth Scorchers"], "side_b": ["Sydney Sixers"], "winner": [None]})
    joined = compare.join(matches, market)
    assert list(joined["match_id"]) == ["x"]


def test_the_page_shape_marks_a_gap_clear_only_when_its_interval_misses_zero():
    from innings.web.routes.market import shape

    def moment(name, low, high):
        return {"moment": name, "n": 10, "brier_model": 0.2, "brier_market": 0.19, "brier_gap": 0.01,
                "brier_gap_interval": [low, high]}

    calibration = {"bins": [{"said": 0.3, "happened": 0.25, "n": 4}], "error": 0.05}
    report = {"matches": {}, "betting": {},
              "moments": [moment("FIRST_BALL", 0.002, 0.02), moment("SECOND_INN_SIX_OV", -0.01, 0.02)],
              "pooled": {"n": 20, "calibration_model": calibration, "calibration_market": calibration,
                         "calibration_gap_interval": [-0.1, 0.1]}}
    page = shape(report)
    assert [m["clear"] for m in page["moments"]] == [True, False]
    assert page["moments"][1]["label"] == "Chase, 6 overs"
    assert {b["model"] for b in page["calibration"]} == {"innings", "market"}
