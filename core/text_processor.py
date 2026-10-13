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
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
