"""Thẻ điều khiển viết ngay trong văn bản.

Hai nhóm:

- **Thẻ cảm xúc** ``[cười]``, ``[thở dài]``, ``[hắng giọng]`` (và bản tiếng Anh
  ``[chuckle]``, ``[sigh]``, ``[clear throat]``): model VieNeu v3 Turbo tự hiểu
  (``phonemize_text_with_emotions`` đổi thành ``<|emotion_1..3|>``), nên app
  **giữ nguyên** trong câu chữ đưa vào model.

- **Thẻ nghỉ** ``[nghỉ 3s]``, ``[nghỉ 1.5 giây]``, ``[nghỉ 500ms]``,
  ``[nghỉ]`` (mặc định 2 giây): app tự cắt câu tại thẻ và chèn khoảng lặng
  **đúng thời lượng** (không phụ thuộc model).

Quy ước:
- Thời lượng thật tính trên bản gốc 1.0x; khi người dùng đổi tốc độ phát thì
  toàn bộ audio (kể cả khoảng lặng) được time-stretch như các khoảng nghỉ khác.
- Kẹp trong khoảng 0.1 - 30 giây để tránh gõ nhầm.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

PAUSE_DEFAULT_SEC = 2.0
PAUSE_MIN_SEC = 0.1
PAUSE_MAX_SEC = 30.0

#: Thẻ cảm xúc hợp lệ (tiếng Việt) — model đã hiểu sẵn.
EMOTION_TAGS: tuple[str, ...] = ("cười", "thở dài", "hắng giọng")
#: Bí danh tiếng Anh do model hỗ trợ.
EMOTION_ALIASES: dict[str, str] = {
    "chuckle": "cười",
    "sigh": "thở dài",
    "clear throat": "hắng giọng",
}

_RE_BRACKET = re.compile(r"\[[^\]\n]{1,60}\]")
_RE_PAUSE = re.compile(
    r"\[\s*(?:nghỉ|nghi|ngắt|ngat|tạm\s*dừng|tam\s*dung|pause)\s*[:=]?\s*"
    r"(\d+(?:[.,]\d+)?)?\s*(ms|mili\s*giây|mili\s*giay|s|giây|giay|g)?\s*\]",
    re.IGNORECASE,
)
_RE_SPACES = re.compile(r"[ \t]{2,}")


@dataclass(frozen=True)
class Piece:
    """Một mảnh trong câu: đọc ``text`` rồi nghỉ ``pause_sec`` giây."""

    text: str
    pause_sec: float = 0.0


def _clamp(sec: float) -> float:
    return min(PAUSE_MAX_SEC, max(PAUSE_MIN_SEC, sec))


def parse_pause_tag(tag: str) -> float | None:
    """``"[nghỉ 3s]"`` -> ``3.0``; không phải thẻ nghỉ -> ``None``."""
    match = _RE_PAUSE.fullmatch(tag.strip())
    if match is None:
        return None
    raw_value, unit = match.group(1), (match.group(2) or "s").lower()
    if raw_value is None:
        return PAUSE_DEFAULT_SEC
    try:
        value = float(raw_value.replace(",", "."))
    except ValueError:
        return PAUSE_DEFAULT_SEC
    if unit.startswith(("ms", "mili")):
        value /= 1000.0
    return _clamp(value)


def has_pause(text: str) -> bool:
    """Văn bản có ít nhất một thẻ nghỉ?"""
    return _RE_PAUSE.search(text) is not None


def split_pieces(text: str) -> list[Piece]:
    """Tách câu tại các thẻ nghỉ; giữ lại phần chữ để đưa vào model.

    ``"Chờ chút [nghỉ 3s] rồi đọc"`` ->
    ``[Piece("Chờ chút", 3.0), Piece(" rồi đọc", 0.0)]``

    Thẻ nghỉ đứng ngay sau một thẻ nghỉ khác thì cộng dồn thời lượng.
    """
    pieces: list[Piece] = []
    cursor = 0
    for match in _RE_PAUSE.finditer(text):
        pause = parse_pause_tag(match.group(0)) or 0.0
        chunk = text[cursor:match.start()]
        if chunk.strip() or not pieces:
            pieces.append(Piece(text=chunk, pause_sec=pause))
        else:
            prev = pieces[-1]
            pieces[-1] = Piece(text=prev.text, pause_sec=prev.pause_sec + pause)
        cursor = match.end()

    tail = text[cursor:]
    if tail.strip() or not pieces:
        pieces.append(Piece(text=tail, pause_sec=0.0))
    return pieces


def clean_for_model(text: str) -> str:
    """Bỏ thẻ nghỉ (đã xử lý riêng) và gộp khoảng trắng thừa.

    Thẻ cảm xúc được GIỮ NGUYÊN vì model tự hiểu.
    """
    stripped = _RE_PAUSE.sub(" ", text)
    return _RE_SPACES.sub(" ", stripped).strip()


def has_speech(text: str) -> bool:
    """Có chữ/số thật để đọc? (loại mảnh chỉ còn dấu câu như ``"."``)"""
    return re.search(r"\w", text, re.UNICODE) is not None


def format_pause(sec: float) -> str:
    """``3.0`` -> ``"[nghỉ 3s]"``; ``1.5`` -> ``"[nghỉ 1.5s]"``."""
    value = _clamp(float(sec))
    number = str(int(value)) if float(value).is_integer() else f"{value:g}"
    return f"[nghỉ {number}s]"


def find_unknown_tags(text: str) -> list[str]:
    """Các ``[...]`` không phải thẻ nghỉ và không phải thẻ cảm xúc đã biết.

    Dùng để cảnh báo (không chặn): model sẽ đọc chúng thành chữ.
    """
    known = {t.lower() for t in EMOTION_TAGS} | set(EMOTION_ALIASES)
    unknown: list[str] = []
    for match in _RE_BRACKET.finditer(text):
        tag = match.group(0)
        if parse_pause_tag(tag) is not None:
            continue
        inner = tag[1:-1].strip().lower()
        if inner in known:
            continue
        if inner.startswith("<|emotion_"):
            continue
        unknown.append(tag)
    return unknown
