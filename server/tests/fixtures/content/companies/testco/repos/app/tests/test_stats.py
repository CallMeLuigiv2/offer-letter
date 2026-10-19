from stats import mean, percentile


def test_mean():
    assert mean([1, 2, 3]) == 2


def test_percentile_sorted():
    assert percentile([1, 2, 3, 4, 5], 50) == 3
