"""Pace-or-spin estimates: the features, and that estimates are only used where they should be."""
import numpy as np
import pytest

from innings.config import DB_PATH
from innings.pace_or_spin import SURE, features


def bowler(**counts):
    row = dict(n=600, wkts=0, stumped=0, behind=0, bowled_lbw=0, own_catch=0, limited=600,
               powerplay=0, middle=0, death=0, test=0, new_ball=0, first_over=0, wides=0,
               noballs=0, byes=0, conceded=0, spell=2.0)
    return row | counts


def test_a_few_wickets_are_pulled_toward_the_average():
    rows = [bowler(wkts=1, stumped=1), bowler(wkts=100, stumped=10), bowler(wkts=100, stumped=0)]
    stumped_share = features(rows)[:, 0]
    assert 0 < stumped_share[0] < 1             # one stumping in one wicket is not 100%
    assert stumped_share[1] == pytest.approx((10 + 5 * 11 / 201) / 105)


def test_missing_formats_take_the_average():
    rows = [bowler(test=0), bowler(test=100, new_ball=50), bowler(test=100, new_ball=10)]
    new_ball_share = features(rows)[:, 7]
    assert not np.isnan(new_ball_share).any()
    assert new_ball_share[0] == pytest.approx((0.5 + 0.1) / 2)


built = pytest.mark.skipif(not DB_PATH.exists(), reason="database not built")


@built
def test_estimates_never_replace_a_known_style():
    from innings.web.db import q
    clash = q("select count(*) as n from ck_balls where family_estimated and bowl_type is not null")
    assert clash[0]["n"] == 0
    both = q("""select count(*) as n from ck_pace_spin g join ck_styles s using (player_id)
                where s.bowl_type is not null""")
    assert both[0]["n"] == 0


@built
def test_sure_estimates_were_right_on_held_out_bowlers():
    from innings.web.db import q
    report = {row["name"]: row["value"] for row in q(
        "select name, value from constants where sport = 'ck' and name like 'pace_spin_%'")}
    assert report["pace_spin_known"] > 1000
    assert report["pace_spin_sure_accuracy"] >= SURE
