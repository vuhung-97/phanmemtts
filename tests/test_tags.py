"""Kiểm thử core/tags.py — thẻ cảm xúc + thẻ nghỉ."""

from __future__ import annotations

import pytest

from core.tags import (
    PAUSE_DEFAULT_SEC,
    PAUSE_MAX_SEC,
    PAUSE_MIN_SEC,
    Piece,
    clean_for_model,
    find_unknown_tags,
    format_pause,
    has_pause,
    has_speech,
    parse_pause_tag,
    split_pieces,
)


@pytest.mark.parametrize("tag,expect", [
    ("[nghỉ 3s]", 3.0),
    ("[nghỉ 1,5 giây]", 1.5),
    ("[nghỉ 2]", 2.0),
    ("[nghỉ 500ms]", 0.5),
    ("[NGHỈ 4S]", 4.0),
    ("[ngắt 2s]", 2.0),
    ("[tạm dừng 1s]", 1.0),
    ("[pause 2s]", 2.0),
    ("[ nghỉ   2 s ]", 2.0),
])
def test_parse_pause_tag_reads_duration(tag, expect):
    assert parse_pause_tag(tag) == pytest.approx(expect)


def test_parse_pause_tag_defaults_and_rejects():
    assert parse_pause_tag("[nghỉ]") == PAUSE_DEFAULT_SEC
    assert parse_pause_tag("[cười]") is None
    assert parse_pause_tag("nghỉ 2s") is None


def test_pause_duration_is_clamped():
    assert parse_pause_tag("[nghỉ 0s]") == PAUSE_MIN_SEC
    assert parse_pause_tag("[nghỉ 99s]") == PAUSE_MAX_SEC


def test_split_pieces_middle_tag():
    pieces = split_pieces("Chờ chút [nghỉ 3s] rồi đọc tiếp.")
    assert [p.pause_sec for p in pieces] == [3.0, 0.0]
    assert pieces[0].text.strip() == "Chờ chút"
    assert pieces[1].text.strip() == "rồi đọc tiếp."


def test_split_pieces_leading_and_trailing_tag():
    leading = split_pieces("[nghỉ 2s] Xin chào.")
    assert leading[0].text == "" and leading[0].pause_sec == 2.0
    assert leading[1].text.strip() == "Xin chào."

    trailing = split_pieces("Tạm biệt [nghỉ 1s]")
    assert len(trailing) == 1
    assert trailing[0].text.strip() == "Tạm biệt"
    assert trailing[0].pause_sec == 1.0


def test_split_pieces_pause_only():
    pieces = split_pieces("[nghỉ 2s]")
    assert pieces == [Piece(text="", pause_sec=2.0)]


def test_split_pieces_consecutive_tags_accumulate():
    pieces = split_pieces("A [nghỉ 1s] [nghỉ 2s] B")
    assert [round(p.pause_sec, 3) for p in pieces] == [3.0, 0.0]


def test_clean_for_model_keeps_emotion_removes_pause():
    text = "Xin chào [cười]  chờ  [nghỉ 2s]  nhé"
    assert clean_for_model(text) == "Xin chào [cười] chờ nhé"


def test_has_speech_ignores_punctuation():
    assert has_speech("Xin chào")
    assert has_speech("[cười]")
    assert not has_speech(".")
    assert not has_speech(" ... ")


def test_format_pause_roundtrip():
    assert format_pause(3) == "[nghỉ 3s]"
    assert format_pause(1.5) == "[nghỉ 1.5s]"
    assert parse_pause_tag(format_pause(2.5)) == pytest.approx(2.5)


def test_has_pause():
    assert has_pause("A [nghỉ 2s] B")
    assert not has_pause("A [cười] B")


def test_find_unknown_tags():
    text = "A [cười] B [abc] C [nghỉ 2s] D [sigh] E [xyz] [uvw]"
    assert find_unknown_tags(text) == ["[abc]", "[xyz]", "[uvw]"]
    assert find_unknown_tags("Không có thẻ") == []
    assert find_unknown_tags("[thẻ 2 lần]") == ["[thẻ 2 lần]"]
