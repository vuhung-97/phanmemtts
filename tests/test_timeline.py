"""Kiểm thử TimelineMap (mốc thời gian theo câu)."""

from __future__ import annotations

from core.models import SentenceItem, TimelineMap


def _timeline() -> TimelineMap:
    return TimelineMap(
        sentences=[
            SentenceItem(index=0, text="a", char_start=0, char_end=1,
                         start_sec=0.0, end_sec=1.0),
            SentenceItem(index=1, text="b", char_start=2, char_end=3,
                         start_sec=1.5, end_sec=3.0),
        ],
        sample_rate=48000,
    )


def test_total_duration():
    assert _timeline().total_duration == 3.0


def test_find_index_by_time():
    tl = _timeline()
    assert tl.find_index_by_time(0.5) == 0
    assert tl.find_index_by_time(1.2) == 0    # nằm trong khoảng lặng -> câu trước
    assert tl.find_index_by_time(2.0) == 1
    assert tl.find_index_by_time(99.0) == 1


def test_scaled_divides_times():
    scaled = _timeline().scaled(2.0)
    assert scaled.sentences[0].end_sec == 0.5
    assert scaled.sentences[1].start_sec == 0.75
    assert scaled.sample_rate == 48000


def test_scaled_by_one_returns_same():
    tl = _timeline()
    assert tl.scaled(1.0) is tl
