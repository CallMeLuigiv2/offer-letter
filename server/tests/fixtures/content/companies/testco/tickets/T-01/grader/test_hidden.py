from report import summarize
from stats import percentile


def test_percentile_sorts_input():
    assert percentile([5, 1, 9, 3, 7], 50) == 5


def test_summarize_empty():
    assert summarize([]) == {"mean_ms": 0.0, "p99_ms": 0.0}
