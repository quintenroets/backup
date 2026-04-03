from backup.utils.itertools import fill_gaps


def test_fill_gaps_empty_source() -> None:
    groups = [(1, iter([2, 3]))]
    result = [list(g) for g in fill_gaps(iter(groups), 2)]
    assert result == [[], [2, 3]]
