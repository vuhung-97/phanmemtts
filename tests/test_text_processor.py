"""Kiểm thử tách câu và dọn văn bản."""

from __future__ import annotations

from core.text_processor import build_sentences, clean_text, split_sentences


def test_split_simple_sentences():
    text = "Câu một. Câu hai! Câu ba?"
    spans = split_sentences(text)
    assert len(spans) == 3
    assert text[spans[0][0]:spans[0][1]] == "Câu một."


def test_abbreviation_keeps_sentence_together():
    # Chữ viết tắt cuối câu ("GS.") không được tách -> câu gộp lại.
    text = "Ông ấy là GS. Nguyễn Văn A đến muộn."
    spans = split_sentences(text)
    assert len(spans) == 1


def test_abbreviation_does_not_swallow_newline():
    # Lỗi cũ: dấu "." viết tắt bỏ qua luôn dấu xuống dòng phía sau.
    text = "Ông ấy là GS.\nNguyễn Văn A đến muộn."
    spans = split_sentences(text)
    assert len(spans) == 2
    assert text[spans[0][0]:spans[0][1]] == "Ông ấy là GS."


def test_decimal_not_split():
    text = "Kết quả là 3.14 rất đẹp."
    spans = split_sentences(text)
    assert len(spans) == 1


def test_build_sentences_keeps_offsets():
    text = "Một. Hai."
    items = build_sentences(text)
    assert [i.text for i in items] == ["Một.", "Hai."]
    for item in items:
        assert text[item.char_start:item.char_end] == item.text


def test_clean_text():
    assert clean_text("a  \t b") == "a b"
    assert clean_text("a\n\n\n\nb") == "a\n\nb"
