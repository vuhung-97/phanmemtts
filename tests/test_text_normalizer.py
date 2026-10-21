"""Kiểm thử chuẩn hóa số/ký hiệu tiếng Việt."""

from __future__ import annotations

from core.text_normalizer import normalize_numbers_vi


def test_plain_integer():
    assert normalize_numbers_vi("2024") == "hai nghìn không trăm hai mươi bốn"


def test_thousand_separator_dot():
    out = normalize_numbers_vi("Giá là 1.500.000 đồng")
    assert "một triệu năm trăm nghìn" in out
    assert "đồng" in out


def test_percent():
    assert normalize_numbers_vi("50%") == "năm mươi phần trăm"


def test_date_dd_mm_yyyy():
    out = normalize_numbers_vi("ngày 05/03/2024")
    assert "năm" in out and "tháng" in out


def test_keeps_non_numeric_text():
    text = "Xin chào các bạn, hôm nay trời đẹp."
    assert normalize_numbers_vi(text) == text
