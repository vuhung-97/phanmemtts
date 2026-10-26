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


# ── Thẻ trong ngoặc vuông phải giữ nguyên (bug #7) ──

def test_pause_tag_not_normalized():
    """[nghỉ 3s] không được thành [nghỉ bas]."""
    assert normalize_numbers_vi("[nghỉ 3s]") == "[nghỉ 3s]"
    out = normalize_numbers_vi("Chờ [nghỉ 3s] rồi đọc 2024")
    assert "[nghỉ 3s]" in out
    assert "hai nghìn không trăm hai mươi bốn" in out


def test_emotion_tag_numbers_not_normalized():
    assert normalize_numbers_vi("Tôi cười 2 lần [cười 2 lần]") == \
        "Tôi cười hai lần [cười 2 lần]"


def test_marker_tag_not_normalized():
    out = normalize_numbers_vi("[P1] Doanh thu 2024")
    assert out.startswith("[P1]")
    assert "hai nghìn" in out


def test_multiple_tags_keep_outer_text_normalized():
    out = normalize_numbers_vi("[a 1] giữa 2 [b 3] cuối 4")
    assert out == "[a 1] giữa hai [b 3] cuối bốn"


def test_unclosed_bracket_does_not_swallow_text():
    """Ngoặc mở mà không đóng -> vẫn chuẩn hoá phần sau như bình thường."""
    assert "hai" in normalize_numbers_vi("Mở ngoặc [ không đóng 2")
