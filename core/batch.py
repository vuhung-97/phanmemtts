"""Chuyển đổi hàng loạt theo marker ``[P1]``, ``[P2]``… ở đầu dòng.

Ví dụ::

    [P1] Phần mở đầu buổi phát thanh.
    Nội dung tiếp theo của phần 1.

    [P2] Phần thứ hai.
    ...

Mỗi marker -> một tệp audio riêng. Văn bản không có marker -> một tệp duy
nhất (giống luồng chuyển đổi thường, nhưng xuất thẳng ra thư mục).

Quy ước:

- Marker không phân biệt hoa/thường (``[p1]`` = ``[P1]``), 1–3 chữ số.
- Phần nằm **trước** marker đầu tiên (nếu có chữ) được coi là ``P0``.
- Phần rỗng (chỉ có marker) bị bỏ qua.
- Tên tệp lấy từ marker + tiền tố người dùng đặt, đã làm sạch ký tự cấm.
"""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

from core.text_processor import build_sentences

_MARKER = re.compile(r"^[ \t]*\[([Pp]\d{1,3})\][ \t]*", re.MULTILINE)
_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_SPACES = re.compile(r"\s+")
_WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
MAX_STEM = 80


@dataclass(frozen=True)
class BatchPart:
    """Một phần của văn bản (một marker hoặc cả văn bản khi không có marker)."""

    marker: str        # "P1", "P0"… hoặc "" khi văn bản không có marker
    text: str
    char_count: int
    sentence_count: int
    start: int = 0
    end: int = 0

    @property
    def label(self) -> str:
        return self.marker or "Toàn bộ"


def _make_part(marker: str, text: str, start: int = 0, end: int = 0) -> BatchPart:
    body = text.strip()
    return BatchPart(
        marker=marker,
        text=body,
        char_count=len(body),
        sentence_count=len(build_sentences(body)),
        start=start,
        end=end,
    )


def parse_batch(text: str) -> list[BatchPart]:
    """Tách ``text`` thành các phần theo marker; bỏ phần rỗng."""
    normalized = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    matches = list(_MARKER.finditer(normalized))
    if not matches:
        part = _make_part("", normalized)
        return [part] if part.text else []

    parts: list[BatchPart] = []
    prefix = normalized[: matches[0].start()]
    if prefix.strip():
        parts.append(_make_part("P0", prefix, 0, matches[0].start()))

    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
        part = _make_part(match.group(1).upper(), normalized[match.end():end],
                          match.end(), end)
        if part.text:
            parts.append(part)
    return parts


def sanitize_filename(name: str, fallback: str = "audio") -> str:
    """Làm sạch một tên tệp cho Windows (giữ dấu tiếng Việt)."""
    cleaned = _ILLEGAL.sub("_", str(name or ""))
    cleaned = _SPACES.sub(" ", cleaned).strip().strip(".")
    if not cleaned:
        cleaned = fallback
    if cleaned.upper() in _WINDOWS_RESERVED:
        cleaned = f"_{cleaned}"
    return cleaned[:MAX_STEM].rstrip(" .") or fallback


def part_filename(part: BatchPart, base: str = "", ext: str = ".mp3",
                  used: set[str] | None = None) -> str:
    """Tên tệp cho một phần, tự thêm ``_2`` khi trùng."""
    stem = sanitize_filename(base)
    if part.marker:
        stem = f"{stem}_{part.marker}" if stem and stem != "audio" else part.marker
    suffix = ext if ext.startswith(".") else f".{ext}"
    candidate = f"{stem}{suffix}"
    if used is None:
        return candidate
    counter = 2
    while candidate.casefold() in used:
        candidate = f"{stem}_{counter}{suffix}"
        counter += 1
    used.add(candidate.casefold())
    return candidate


def write_zip(files: list[str | Path], zip_path: str | Path) -> Path:
    """Đóng gói các tệp đã xuất thành một tệp .zip (không nén audio)."""
    target = Path(zip_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED) as archive:
        for item in files:
            path = Path(item)
            archive.write(path, arcname=path.name)
    return target
