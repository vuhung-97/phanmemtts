"""Chuẩn hóa số/ký hiệu trong văn bản thành chữ tiếng Việt trước khi đọc.

Vì sao cần: bộ từ vựng của model TTS không chứa ký tự số
0-9, số phải được chuyển thành chữ ("2024" -> "hai nghìn không trăm
hai mươi bốn") thì mô hình mới phát âm được.

Ngày tháng được nhận cả ba dạng: dd/mm/yyyy, dd-mm-yyyy và ISO
yyyy-mm-dd (chỉ chuyển khi ngày 1-31, tháng 1-12 hợp lệ).

Chỉ dùng ở tầng đưa vào mô hình TTS — văn bản hiển thị trên giao diện
và các mốc char_start/char_end của TimelineMap giữ nguyên, nên highlight
karaoke vẫn bám đúng câu.
"""

from __future__ import annotations

import re

from num2words import num2words

_DATE_ISO = re.compile(r"\b(?:(ngày)\s+)?(\d{4})-(\d{1,2})-(\d{1,2})\b", re.IGNORECASE)
_DATEDDMMYY = re.compile(r"\b(?:(ngày)\s+)?(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b", re.IGNORECASE)
_DATEDDMM = re.compile(r"\b(?:(ngày)\s+)?(\d{1,2})[/-](\d{1,2})\b", re.IGNORECASE)
_PERCENT = re.compile(r"(\d+(?:[.,]\d+)?)\s*%")
_MONEY_UNIT = re.compile(
    r"\b(\d{1,3}(?:\.\d{3})+|\d+)\s*(k|nghìn|ngàn|triệu|tỷ|vnđ|đ|đồng)\b",
    re.IGNORECASE,
)
_THOUSANDS_DOT = re.compile(r"\b\d{1,3}(?:\.\d{3})+\b")
_THOUSANDS_COMMA = re.compile(r"\b\d{1,3}(?:,\d{3})+\b")
_DECIMAL = re.compile(r"\b\d+(?:[.,]\d+)\b")
_INTEGER = re.compile(r"\b\d+\b")

_UNIT_WORDS = {
    "k": "nghìn",
    "nghìn": "nghìn",
    "ngàn": "ngàn",
    "triệu": "triệu",
    "tỷ": "tỷ",
    "vnđ": "đồng",
    "đ": "đồng",
    "đồng": "đồng",
}


def _fix_natural_vietnamese(text: str) -> str:
    """Sửa các quy tắc đọc số chuẩn miền Bắc / chuẩn văn bản:

    - 2024: 'hai nghìn lẻ hai mươi bốn' -> 'hai nghìn không trăm hai mươi bốn'
    - 2015: 'hai nghìn lẻ mười lăm' -> 'hai nghìn không trăm mười lăm'
    (Chỉ giữ 'lẻ' khi số hàng chục bằng 0: 2005 -> 'hai nghìn lẻ năm')
    """
    # nghìn/triệu/tỷ lẻ [X mươi ...] -> không trăm [X mươi ...]
    text = re.sub(r"\b(nghìn|triệu|tỷ)\s+lẻ\s+([a-zà-ỹ]+\s+mươi\b)", r"\1 không trăm \2", text)
    # nghìn/triệu/tỷ lẻ mười [...] -> không trăm mười [...]
    text = re.sub(r"\b(nghìn|triệu|tỷ)\s+lẻ\s+(mười\b)", r"\1 không trăm \2", text)
    return text


def _int_to_words(value: int) -> str:
    res = num2words(value, lang="vi")
    return _fix_natural_vietnamese(res)


def _number_to_words(raw: str) -> str:
    """'1.500.000' | '1,500,000' | '3,14' | '2024' -> chữ tiếng Việt chuẩn."""
    cleaned = (
        raw.replace(".", "").replace(",", ".")
        if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", raw)
        else raw.replace(",", ".")
    )
    try:
        value = float(cleaned)
    except ValueError:
        return raw
    if value.is_integer() and abs(value) <= 1e15:
        return _int_to_words(int(value))
    res = num2words(value, lang="vi")
    return _fix_natural_vietnamese(res)


def normalize_numbers_vi(text: str) -> str:
    """Chuyển mọi số trong văn bản thành chữ tiếng Việt chuẩn."""

    def _date_iso(match: re.Match) -> str:
        orig_prefix = match.group(1)
        year, month, day = int(match.group(2)), int(match.group(3)), int(match.group(4))
        if not (1 <= day <= 31 and 1 <= month <= 12):
            return match.group(0)
        prefix = f"{orig_prefix} " if orig_prefix else "ngày "
        return f"{prefix}{_int_to_words(day)} tháng {_int_to_words(month)} năm {_int_to_words(year)}"

    def _date_with_year(match: re.Match) -> str:
        orig_prefix = match.group(1)
        day, month = int(match.group(2)), int(match.group(3))
        if not (1 <= day <= 31 and 1 <= month <= 12):
            return match.group(0)
        year = int(match.group(4))
        if len(match.group(4)) == 2:
            year += 2000 if year < 30 else 1900
        prefix = f"{orig_prefix} " if orig_prefix else ""
        return f"{prefix}{_int_to_words(day)} tháng {_int_to_words(month)} năm {_int_to_words(year)}"

    def _date_no_year(match: re.Match) -> str:
        orig_prefix = match.group(1)
        day, month = int(match.group(2)), int(match.group(3))
        if not (1 <= day <= 31 and 1 <= month <= 12):
            return match.group(0)
        prefix = f"{orig_prefix} " if orig_prefix else ""
        return f"{prefix}{_int_to_words(day)} tháng {_int_to_words(month)}"

    text = _DATE_ISO.sub(_date_iso, text)
    text = _DATEDDMMYY.sub(_date_with_year, text)
    text = _DATEDDMM.sub(_date_no_year, text)
    text = _PERCENT.sub(
        lambda m: f"{_number_to_words(m.group(1))} phần trăm", text
    )

    def _money_match(match: re.Match) -> str:
        unit = _UNIT_WORDS.get(match.group(2).lower(), match.group(2))
        return f"{_number_to_words(match.group(1))} {unit}"

    text = _MONEY_UNIT.sub(_money_match, text)
    text = _THOUSANDS_DOT.sub(lambda m: _number_to_words(m.group(0)), text)
    text = _THOUSANDS_COMMA.sub(lambda m: _number_to_words(m.group(0)), text)
    text = _DECIMAL.sub(lambda m: _number_to_words(m.group(0)), text)
    text = _INTEGER.sub(lambda m: _number_to_words(m.group(0)), text)
    return text
