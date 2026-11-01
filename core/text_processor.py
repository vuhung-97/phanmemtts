from __future__ import annotations

import re

from .models import SentenceItem

_SENTENCE_END = re.compile(r"[.!?…]+")
_ABBREVIATIONS = {
    "tp", "q", "p", "ts", "bs", "gs", "pgs", "ths", "ks", "mrs", "mr", "dr",
    "vd", "khi", "v v", "tp.hcm", "ttpm",
}
_DIGIT = re.compile(r"\d")


def split_sentences(text: str) -> list[tuple[int, int]]:
    """Trả về danh sách (char_start, char_end) của từng câu trong văn bản gốc."""
    spans: list[tuple[int, int]] = []
    start = 0
    length = len(text)
    i = 0
    while i < length:
        ch = text[i]
        if ch == "\n":
            _push(spans, text, start, i)
            start = i + 1
            i += 1
            continue
        if ch in ".!?…":
            end = i + 1
            while end < length and text[end] in ".!?…":
                end += 1
            if end < length and text[end] == '"':
                end += 1
            if _is_sentence_boundary(text, start, i, end):
                _push(spans, text, start, end)
                start = end
                i = end
                continue
            # Không phải ranh giới câu (vd "GS." — chữ viết tắt).
            # Chỉ tiến 1 ký tự để không bỏ qua dấu xuống dòng phía sau.
            i += 1
            continue
        i += 1
    _push(spans, text, start, length)
    return spans


def _is_sentence_boundary(text: str, sent_start: int, dot_pos: int, end: int) -> bool:
    token = text[sent_start:dot_pos].rsplit(None, 1)[-1] if text[sent_start:dot_pos].strip() else ""
    if _DIGIT.search(token) and _DIGIT.search(text[end:end + 2] or "x"):
        return False
    if token.lower().strip(".") in _ABBREVIATIONS and token.lower() != token:
        return False
    rest = text[end:].lstrip()
    if rest and rest[0].islower() and rest[0] not in "\"'“”":
        return False
    return True


def _push(spans: list[tuple[int, int]], text: str, start: int, end: int) -> None:
    raw = text[start:end]
    left = len(raw) - len(raw.lstrip())
    right = len(raw.rstrip())
    char_start = start + left
    char_end = start + right
    if char_start < char_end:
        spans.append((char_start, char_end))


def build_sentences(text: str) -> list[SentenceItem]:
    return [
        SentenceItem(
            index=idx,
            text=text[a:b],
            char_start=a,
            char_end=b,
        )
        for idx, (a, b) in enumerate(split_sentences(text))
    ]


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ── Làm sạch để đọc (nút "Làm sạch văn bản") ──

#: Ký tự kết thúc câu -> dòng sau là câu mới, không gộp.
_TERMINAL_END = ".?!…:;\"')]}»"
#: Dòng mở đầu bằng bullet / số thứ tự -> giữ nguyên dòng riêng.
_BULLET_START = re.compile(r"^\s{0,3}(?:[-*+•–]|\d+[.)])\s+")
#: Dòng chỉ gồm thẻ điều khiển (``[nghỉ 2s]``) -> không gộp.
_ONLY_TAGS = re.compile(r"^\s*(?:\[[^\]\n]{1,60}\]\s*)+$")
#: Dòng kịch bản hội thoại ``Tên: nội dung`` -> không gộp với dòng trước.
_SPEAKER_LINE = re.compile(r"^\s*[^:\n]{1,40}:\s+\S")
#: Ký tự cho phép gộp dòng sau dù chữ đầu viết hoa.
_SOFT_END = ",([—-"
_SPACES = re.compile(r"[ \t]{2,}")


#: Thẻ điều khiển ở cuối dòng -> bỏ qua khi xét dấu kết câu.
_TRAILING_TAGS = re.compile(r"(?:\s*\[[^\]\n]{1,60}\])+\s*$")


def _should_join(prev: str, cur: str) -> bool:
    """Dòng ``cur`` là phần tiếp theo của câu ở dòng ``prev``?"""
    if not prev or not cur:
        return False
    if _ONLY_TAGS.match(prev) or _ONLY_TAGS.match(cur):
        return False
    if _SPEAKER_LINE.match(cur):
        return False
    if _BULLET_START.match(cur):
        return False
    # "Xin chào [cười]" -> xét dấu kết câu của phần chữ trước thẻ
    probe = _TRAILING_TAGS.sub("", prev).rstrip() or prev
    if probe[-1] in _TERMINAL_END:
        return False
    if probe[-1] in _SOFT_END:
        return True
    return cur[0].islower()



def clean_for_reading(text: str) -> tuple[str, int]:
    """Làm sạch văn bản để đọc tự nhiên hơn.

    - Bỏ dòng trống thừa (giữ tối đa 1 dòng trống giữa các đoạn).
    - Gộp dòng bị ngắt giữa câu (dòng trước không kết thúc câu và dòng sau
      bắt đầu bằng chữ thường) -> model không ngắt hơi giữa câu.
    - **Giữ nguyên**: bullet/số thứ tự, tiêu đề viết hoa, công thức kiểu
      ``1 + 1``, nội dung trong ngoặc vuông (thẻ điều khiển).
    - Gộp khoảng trắng thừa, bỏ khoảng trắng cuối dòng.

    Trả ``(văn_bản_mới, số_thay_đổi)`` — số thay đổi = số dòng đã gộp/bỏ.
    """
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.replace("\u00a0", " ")
    lines = [line.rstrip() for line in normalized.split("\n")]

    out: list[str] = []
    changes = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if out and out[-1] == "":
                changes += 1
                continue
            if out:
                out.append("")
            continue
        if out and out[-1] and _should_join(out[-1], stripped):
            out[-1] = f"{out[-1]} {stripped}"
            changes += 1
        else:
            out.append(stripped)

    while out and out[0] == "":
        out.pop(0)
    while out and out[-1] == "":
        out.pop()

    result = _SPACES.sub(" ", "\n".join(out)).strip()
    return result, changes

