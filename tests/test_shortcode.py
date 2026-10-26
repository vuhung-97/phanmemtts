"""Kiểm thử mã kích hoạt 15 ký tự (codec Crockford + shortcode)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from core.licensing import codec, shortcode

M24 = 0x123456


def _encode_prefix(prefix: int) -> str:
    value = (prefix << 36) | shortcode._tag(prefix)
    return codec.group(codec.encode_int(value, 15), 5)


# ── Codec ──

def test_codec_roundtrip():
    for value in (0, 1, 31, 32, 0xFFFFFF, (1 << 75) - 1):
        text = codec.encode_int(value, 15)
        assert codec.decode_text(text, 15) == value


def test_codec_normalize_va_nhom():
    assert codec.normalize(" 7k2qf-9m3xa ") == "7K2QF9M3XA"
    assert codec.normalize("OILU") == "011V"
    assert codec.group("7K2QF9M3XAB8T1Z") == "7K2QF-9M3XA-B8T1Z"


def test_codec_sai_do_dai():
    with pytest.raises(ValueError):
        codec.decode_text("ABC", 15)
    with pytest.raises(ValueError):
        codec.decode_text("A" * 16, 15)


def test_codec_gia_tri_vuot_do_dai():
    with pytest.raises(ValueError):
        codec.encode_int(1 << 20, 3)


# ── Sinh mã ──

def test_issue_7_ngay():
    today = date(2026, 5, 1)
    code = shortcode.issue(M24, shortcode.KIND_WEEK, today=today)
    parsed = shortcode.decode(code)
    assert parsed.kind == shortcode.KIND_WEEK
    assert parsed.machine24 == M24
    assert parsed.expiry_date() == today + timedelta(days=7)


def test_issue_30_ngay():
    today = date(2026, 5, 1)
    parsed = shortcode.decode(
        shortcode.issue(M24, shortcode.KIND_MONTH, today=today))
    assert parsed.expiry_date() == today + timedelta(days=30)
    assert parsed.label == "30 ngày"


def test_issue_vinh_vien():
    parsed = shortcode.decode(shortcode.issue(M24, shortcode.KIND_LIFETIME))
    assert parsed.is_lifetime
    assert parsed.expiry_date() is None
    assert parsed.is_expired(date(2099, 1, 1)) is False
    assert parsed.days_left(date(2099, 1, 1)) is None


def test_issue_tuy_chinh():
    today = date(2026, 5, 1)
    code = shortcode.issue(M24, shortcode.KIND_CUSTOM, days=90, today=today)
    parsed = shortcode.decode(code)
    assert parsed.kind == shortcode.KIND_CUSTOM
    assert parsed.expiry_date() == today + timedelta(days=90)


@pytest.mark.parametrize("days", [0, -1, 3651])
def test_issue_tuy_chinh_sai_so_ngay(days):
    with pytest.raises(ValueError):
        shortcode.issue(M24, shortcode.KIND_CUSTOM, days=days)


def test_issue_vuot_gioi_han_2038():
    with pytest.raises(ValueError):
        shortcode.issue(M24, shortcode.KIND_WEEK, today=date(2038, 3, 1))


def test_issue_khong_doi_khi_cung_dau_vao():
    today = date(2026, 5, 1)
    a = shortcode.issue(M24, shortcode.KIND_MONTH, today=today)
    b = shortcode.issue(M24, shortcode.KIND_MONTH, today=today)
    assert a == b


def test_dinh_dang_3_nhom_5():
    code = shortcode.issue(M24, shortcode.KIND_WEEK)
    assert len(code) == 17            # 15 ký tự + 2 dấu gạch
    parts = code.split("-")
    assert [len(p) for p in parts] == [5, 5, 5]
    assert shortcode.format_code(codec.normalize(code)) == code


# ── Xác thực ──

def test_sua_mot_ky_tu_bi_tu_choi():
    code = codec.normalize(shortcode.issue(M24, shortcode.KIND_WEEK))
    vi_tri = 3
    cu = code[vi_tri]
    moi = "A" if cu != "A" else "B"
    hong = code[:vi_tri] + moi + code[vi_tri + 1:]
    with pytest.raises(shortcode.InvalidCode):
        shortcode.decode(hong)


def test_sua_mot_bit_bi_tu_choi():
    code = shortcode.issue(M24, shortcode.KIND_MONTH)
    value = codec.decode_text(code, 15) ^ 1
    with pytest.raises(shortcode.InvalidCode):
        shortcode.decode(codec.encode_int(value, 15))


def test_nhap_chu_thuong_va_khoang_trang():
    code = shortcode.issue(M24, shortcode.KIND_WEEK)
    parsed = shortcode.decode(" " + code.lower() + " ")
    assert parsed.machine24 == M24


def test_nhap_O_thay_cho_0():
    code = codec.normalize(shortcode.issue(M24, shortcode.KIND_WEEK))
    thay_the = code.replace("0", "O").replace("1", "I")
    parsed = shortcode.decode(thay_the)
    assert parsed.machine24 == M24


def test_phien_ban_khong_ho_tro():
    prefix = (0 << 38) | (shortcode.KIND_WEEK << 36) | (100 << 24) | M24
    with pytest.raises(shortcode.InvalidCode):
        shortcode.decode(_encode_prefix(prefix))


def test_han_dung_0_khong_hop_le():
    prefix = (1 << 38) | (shortcode.KIND_WEEK << 36) | (0 << 24) | M24
    with pytest.raises(shortcode.InvalidCode):
        shortcode.decode(_encode_prefix(prefix))


def test_han_dung_bien():
    today = date(2026, 5, 1)
    parsed = shortcode.decode(
        shortcode.issue(M24, shortcode.KIND_WEEK, today=today))
    assert parsed.is_expired(today + timedelta(days=7)) is False
    assert parsed.is_expired(today + timedelta(days=8)) is True
    assert parsed.days_left(today) == 7
    assert parsed.days_left(today + timedelta(days=6)) == 1


def test_ma_cua_may_khac_van_giai_ma_duoc():
    """Mã đúng chữ ký nhưng khác máy: decode OK, guard mới là nơi báo lỗi."""
    parsed = shortcode.decode(shortcode.issue(0xABCDEF, shortcode.KIND_WEEK))
    assert parsed.machine24 == 0xABCDEF
