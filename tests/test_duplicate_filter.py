from datetime import datetime, timedelta

from detection.duplicate_filter import DuplicateFilter


def test_duplicate_interval() -> None:
    filter_ = DuplicateFilter(10)
    start = datetime(2026, 1, 1, 12, 0, 0)
    assert filter_.accept("ABC-1234", start)
    assert not filter_.accept("ABC-1234", start + timedelta(seconds=9))
    assert filter_.accept("ABC-1234", start + timedelta(seconds=10))