"""Hand tags: what is accepted, which tag counts, joining to Cricsheet, agreement, backup."""
import gzip

import duckdb
import pytest

from innings import tagging
from innings.tagging import agreement, append, backup, check, join, kappa, latest

SCORED = dict(runs=1, wide=False, noball=False, wicket=False)


def tag(**given):
    return dict(tagger="ann", match_id="m1", innings=1, over=19, ball=1, scored=SCORED,
                tags={"length": "yorker", "shot": "drive"}) | given


def test_a_good_tag_names_every_field():
    clean = check(tag())
    assert clean["tags"]["length"] == "yorker"
    assert clean["tags"]["line"] is None            # not seen is stored as None
    assert set(clean["tags"]) == set(tagging.FIELDS)


@pytest.mark.parametrize("bad", [
    dict(tagger="Ann Smith"),
    dict(over="19"),
    dict(tags={"length": "very full"}),
    dict(tags={"swing": "in"}),
    dict(scored={"runs": 1}),
    dict(clock="7pm"),
])
def test_bad_tags_are_refused(bad):
    with pytest.raises(ValueError):
        check(tag(**bad))


def test_the_latest_tag_for_a_ball_counts(tmp_path):
    log = tmp_path / "log.jsonl"
    append(tag(), log)
    append(tag(tags={"length": "full"}), log)
    append(tag(tagger="bob"), log)
    tags = latest(log)
    assert len(tags) == 2
    assert tags[("ann", "m1", 1, 19, 1)]["tags"]["length"] == "full"
    assert len(log.read_text().splitlines()) == 3   # nothing is ever overwritten


def test_join_queues_what_a_person_must_check():
    con = duckdb.connect()
    con.execute("""create table ck_ev as select * from (values
        ('m1', 1, 19, 1, 1, false, false, null),
        ('m1', 1, 19, 2, 4, false, false, null),
        ('m1', 1, 19, 3, 0, false, false, 'bowled'))
        t(match_id, innings, "over", ball, runs, wide, noball, dismissal)""")
    tags = [check(tag()), check(tag(ball=2)), check(tag(ball=3, differs=True)),
            check(tag(ball=4))]
    tags[2]["scored"] = dict(SCORED, runs=0, wicket=True)
    report = join(con, tags)
    reasons = [item["reason"] for item in report["queue"]]
    assert reasons == ["score changed", "tagger saw it differently", "no such ball"]
    assert report["joined"] == 2                      # ball 3 joins, but is still queued


def test_kappa_matches_worked_examples():
    values = ("a", "b")
    assert kappa([("a", "a"), ("b", "b")] * 5, values, False) == 1
    # 20 items, 15 agree; each rater says 'a' half the time: chance agreement is 0.5
    pairs = [("a", "a")] * 8 + [("b", "b")] * 7 + [("a", "b")] * 2 + [("b", "a")] * 3
    assert kappa(pairs, values, False) == pytest.approx(1 - 0.25 / 0.5)
    assert kappa([], values, False) is None


def test_weighted_kappa_counts_near_misses_as_half_wrong():
    values = ("full", "good", "short")
    near = [("full", "full"), ("good", "good"), ("short", "short"), ("full", "good")] * 3
    far = [("full", "full"), ("good", "good"), ("short", "short"), ("full", "short")] * 3
    assert kappa(near, values, True) > kappa(far, values, True)
    assert kappa(near, values, True) > kappa(near, values, False)


def test_agreement_uses_balls_both_taggers_saw(tmp_path):
    log = tmp_path / "log.jsonl"
    for ball in (1, 2):
        append(tag(ball=ball), log)
        append(tag(tagger="bob", ball=ball), log)
    append(tag(ball=3), log)                          # only ann saw ball 3
    append(tag(tagger="bob", ball=1, tags={"length": "full", "shot": None}), log)
    report = agreement(latest(log), "ann", "bob")
    assert report["balls"] == 2
    assert report["fields"]["length"]["agreed"] == 0.5
    assert report["fields"]["shot"]["balls"] == 1     # bob did not see the shot on ball 1


def test_backup_reads_back_as_the_log(tmp_path):
    log = tmp_path / "log.jsonl"
    append(tag(), log)
    append(tag(ball=2), log)
    copy = backup(tmp_path / "copies", log)
    with gzip.open(copy, "rt") as f:
        assert f.read() == log.read_text()
