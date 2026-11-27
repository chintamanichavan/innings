"""The build comparison must see real changes and ignore row order and float noise."""
import duckdb
import pytest

from innings.measure import compare


def database(path, rows):
    con = duckdb.connect(str(path))
    con.execute("create table t (k integer, name varchar, v double)")
    con.executemany("insert into t values (?, ?, ?)", rows)
    con.close()
    return path


ROWS = [(1, "a", 0.1), (2, "b", -0.25), (3, "c", 2.5)]


@pytest.mark.parametrize("changed, same", [
    (ROWS[::-1], True),                                        # row order does not matter
    ([(1, "a", 0.1 + 1e-15), *ROWS[1:]], True),               # float noise is ignored
    ([(1, "a", 0.101), *ROWS[1:]], False),                    # a real float change is not
    ([(1, "z", 0.1), *ROWS[1:]], False),                      # nor a text change
    (ROWS[:2], False),                                        # nor a missing row
    ([*ROWS, ROWS[0]], False),                                # nor a duplicated one
])
def test_compare_sees_changes_and_ignores_noise(tmp_path, changed, same):
    old = database(tmp_path / "old.duckdb", ROWS)
    new = database(tmp_path / "new.duckdb", changed)
    report = compare(old, new)
    assert (report["equal"] == ["t"]) is same
    assert (report["differ"] == {}) is same


def test_compare_lists_tables_on_one_side_only(tmp_path):
    old = database(tmp_path / "old.duckdb", ROWS)
    new = database(tmp_path / "new.duckdb", ROWS)
    con = duckdb.connect(str(new))
    con.execute("create table extra (x integer)")
    con.close()
    assert compare(old, new)["only_new"] == ["extra"]
