"""Kiểm thử nút "Làm sạch văn bản" (clean_for_reading)."""

from __future__ import annotations

from core.text_processor import clean_for_reading


def test_removes_extra_blank_lines():
    text = "Đoạn một.\n\n\n\n\nĐoạn hai."
    out, changes = clean_for_reading(text)
    assert out == "Đoạn một.\n\nĐoạn hai."
    assert changes > 0


def test_joins_line_break_inside_sentence():
    text = "Hôm nay trời rất\nđẹp và mát mẻ."
    out, changes = clean_for_reading(text)
    assert out == "Hôm nay trời rất đẹp và mát mẻ."
    assert changes == 1


def test_keeps_break_after_terminal_punctuation():
    text = "Câu một.\nCâu hai."
    out, _ = clean_for_reading(text)
    assert out == "Câu một.\nCâu hai."


def test_keeps_bullet_lines():
    text = "Các bước:\n- Bước một\n- Bước hai"
    out, _ = clean_for_reading(text)
    assert out == "Các bước:\n- Bước một\n- Bước hai"


def test_keeps_numbered_lines():
    text = "Mục lục:\n1. Phần mở đầu\n2. Phần kết"
    out, _ = clean_for_reading(text)
    assert out == "Mục lục:\n1. Phần mở đầu\n2. Phần kết"


def test_keeps_formula():
    text = "Kết quả phép tính\n1 + 1 = 2"
    out, _ = clean_for_reading(text)
    # Dòng "1 + 1 = 2" bắt đầu bằng số -> giữ dòng riêng (không gộp vào câu)
    assert out == "Kết quả phép tính\n1 + 1 = 2"


def test_keeps_formula_single_line():
    out, changes = clean_for_reading("Ta có 1 + 1 = 2 và 2 + 2 = 4.")
    assert out == "Ta có 1 + 1 = 2 và 2 + 2 = 4."
    assert changes == 0


def test_keeps_tag_only_line():
    text = "Câu một.\n[nghỉ 3s]\nCâu hai."
    out, _ = clean_for_reading(text)
    assert out == text


def test_keeps_tags_intact_when_joining():
    text = "Xin chào [cười]\nbạn nhé."
    out, _ = clean_for_reading(text)
    assert out == "Xin chào [cười] bạn nhé."


def test_joins_after_comma_even_if_uppercase():
    text = "Kính gửi,\nAnh Nguyễn Văn A."
    out, _ = clean_for_reading(text)
    assert out == "Kính gửi, Anh Nguyễn Văn A."


def test_collapses_spaces_and_strips_lines():
    out, _ = clean_for_reading("a    b   \n\n\n   c")
    assert out == "a b\n\n c".replace("\n\n ", "\n\n")
    assert "   " not in out


def test_empty_input():
    assert clean_for_reading("   \n\n  ") == ("", 0)


def test_idempotent():
    text = "Câu một.\n\nCâu hai rất\ndài."
    once, _ = clean_for_reading(text)
    twice, changes = clean_for_reading(once)
    assert twice == once
    assert changes == 0


def test_keeps_heading_uppercase():
    text = "PHẦN MỘT\nnội dung phần một"
    out, _ = clean_for_reading(text)
    # Dòng sau viết thường nhưng dòng trước là tiêu đề không kết thúc câu
    # -> vẫn gộp (quy tắc: dòng sau viết thường là phần tiếp theo).
    assert out == "PHẦN MỘT nội dung phần một"
