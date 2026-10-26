"""Base32 Crockford — mã hoá chuỗi ngắn, chống nhầm ký tự.

Bảng chữ cái bỏ các ký tự dễ nhầm: I, L, O, U.
Khi người dùng nhập, tự quy đổi: O→0, I/L→1, U→V (đúng quy ước Crockford).
"""

from __future__ import annotations

ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_INDEX = {ch: i for i, ch in enumerate(ALPHABET)}
_MAP = {"O": "0", "I": "1", "L": "1", "U": "V"}


def normalize(text: str) -> str:
    """Bỏ mọi ký tự ngoài [A-Z0-9], uppercase và quy đổi ký tự dễ nhầm."""
    out = []
    for ch in (text or "").upper():
        if "0" <= ch <= "9" or "A" <= ch <= "Z":
            out.append(_MAP.get(ch, ch))
    return "".join(out)


def encode_int(value: int, length: int) -> str:
    """Mã hoá số nguyên không âm thành đúng `length` ký tự Crockford."""
    if value < 0:
        raise ValueError("Giá trị âm không mã hoá được")
    if length <= 0:
        raise ValueError("Độ dài phải dương")
    chars = []
    for _ in range(length):
        chars.append(ALPHABET[value & 31])
        value >>= 5
    if value:
        raise ValueError("Giá trị vượt quá độ dài cho phép")
    return "".join(reversed(chars))


def decode_text(text: str, length: int) -> int:
    """Giải mã chuỗi Crockford, trả về số nguyên. Sai độ dài/ký tự -> ValueError."""
    cleaned = normalize(text)
    if len(cleaned) != length:
        raise ValueError(f"Phải có đúng {length} ký tự (đang {len(cleaned)})")
    value = 0
    for ch in cleaned:
        try:
            digit = _INDEX[ch]
        except KeyError:
            raise ValueError(f"Ký tự không hợp lệ: {ch}") from None
        value = (value << 5) | digit
    return value


def group(text: str, size: int = 5, sep: str = "-") -> str:
    """Chia chuỗi thành từng nhóm cho dễ đọc: 7K2QF-9M3XA."""
    return sep.join(text[i:i + size] for i in range(0, len(text), size))
