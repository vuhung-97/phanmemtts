"""Từ điển phát âm: thay cách viết trước khi đưa văn bản vào model TTS.

Ví dụ ``KTX`` -> ``ký túc xá``, ``TP.HCM`` -> ``thành phố Hồ Chí Minh``.

Quy tắc:

- Thay **trước** bước chuẩn hoá số (``core.text_normalizer``) để chữ thay thế
  vẫn được đọc đúng, và để từ viết tắt không bị normalizer cắt nhỏ.
- Mặc định thay theo **nguyên từ** (``\\b`` kiểu Unicode) để ``KTX`` không
  khớp bên trong ``KTXL``.
- **Không** thay bên trong ngoặc vuông: ``[nghỉ 3s]``, ``[P1]``, ``[cười]``
  là cú pháp điều khiển của app/model.
- Cụm dài được thay trước cụm ngắn (``TP.HCM`` trước ``TP``).

Tệp lưu: ``data_dir()/pronunciation-dict.json`` (dùng chung cho mọi giọng).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from core.paths import data_dir

DICT_FILENAME = "pronunciation-dict.json"
DICT_VERSION = 1
MAX_SOURCE_LEN = 60
MAX_TARGET_LEN = 200

#: Nội dung trong ngoặc vuông là thẻ điều khiển — giữ nguyên.
_RE_TAG_SPAN = re.compile(r"\[[^\]\n]{1,60}\]")

#: Cache theo (mtime) để không đọc đĩa mỗi câu.
_cache: tuple[float, dict] | None = None


# ── Đường dẫn & đọc/ghi ──


def dictionary_path() -> Path:
    return data_dir() / DICT_FILENAME


def empty_doc() -> dict:
    return {"ver": DICT_VERSION, "enabled": True, "entries": []}


def normalize_doc(data: object) -> dict:
    """Chuẩn hoá dữ liệu đọc từ JSON; bỏ mục không hợp lệ thay vì ném lỗi."""
    doc = empty_doc()
    if not isinstance(data, dict):
        return doc
    doc["enabled"] = bool(data.get("enabled", True))
    raw_entries = data.get("entries")
    if not isinstance(raw_entries, list):
        return doc
    entries: list[dict] = []
    seen: set[str] = set()
    for item in raw_entries:
        if not isinstance(item, dict):
            continue
        try:
            src, dst = validate_entry(item.get("from", ""), item.get("to", ""))
        except ValueError:
            continue
        key = src if item.get("case_sensitive") else src.casefold()
        if key in seen:
            continue
        seen.add(key)
        entries.append({
            "from": src,
            "to": dst,
            "case_sensitive": bool(item.get("case_sensitive", False)),
            "whole_word": bool(item.get("whole_word", True)),
        })
    doc["entries"] = entries
    return doc


def load(path: Path | None = None) -> dict:
    """Đọc từ điển. Tệp thiếu/hỏng -> từ điển rỗng (không làm sập app)."""
    target = Path(path) if path is not None else dictionary_path()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return empty_doc()
    return normalize_doc(data)


def save(doc: dict, path: Path | None = None) -> None:
    """Ghi từ điển xuống đĩa (atomic qua tệp tạm)."""
    target = Path(path) if path is not None else dictionary_path()
    clean = normalize_doc(doc)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(clean, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    tmp.replace(target)
    global _cache
    _cache = None


def active_doc() -> dict:
    """Từ điển đang dùng (cache theo mtime)."""
    global _cache
    path = dictionary_path()
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return empty_doc()
    if _cache is not None and _cache[0] == mtime:
        return _cache[1]
    doc = load(path)
    _cache = (mtime, doc)
    return doc


def invalidate_cache() -> None:
    global _cache
    _cache = None


# ── Kiểm tra một mục ──


def validate_entry(source: str, target: str) -> tuple[str, str]:
    """Trả ``(from, to)`` đã strip; ném ``ValueError`` nếu không hợp lệ."""
    src = str(source or "").strip()
    dst = str(target or "").strip()
    if not src:
        raise ValueError("Cụm cần thay không được để trống.")
    if not dst:
        raise ValueError("Cách đọc thay thế không được để trống.")
    if len(src) > MAX_SOURCE_LEN:
        raise ValueError(f"Cụm cần thay quá dài (tối đa {MAX_SOURCE_LEN} ký tự).")
    if len(dst) > MAX_TARGET_LEN:
        raise ValueError(f"Cách đọc quá dài (tối đa {MAX_TARGET_LEN} ký tự).")
    if "[" in src or "]" in src or "[" in dst or "]" in dst:
        raise ValueError("Không dùng ngoặc vuông trong từ điển (trùng cú pháp thẻ).")
    return src, dst


# ── Áp dụng ──


def _compile(entries: list[dict]) -> list[tuple[re.Pattern[str], str]]:
    """Biên dịch danh sách mục, cụm dài trước cụm ngắn."""
    ordered = sorted(
        entries,
        key=lambda e: (-len(e["from"]), e["from"].casefold()),
    )
    rules: list[tuple[re.Pattern[str], str]] = []
    seen: set[tuple[str, bool, bool]] = set()
    for entry in ordered:
        src = entry["from"]
        key = (src.casefold() if not entry["case_sensitive"] else src,
               entry["case_sensitive"], entry["whole_word"])
        if key in seen:
            continue
        seen.add(key)
        pattern = re.escape(src)
        if entry["whole_word"]:
            pattern = rf"(?<!\w){pattern}(?!\w)"
        flags = 0 if entry["case_sensitive"] else re.IGNORECASE
        rules.append((re.compile(pattern, flags), entry["to"]))
    return rules


def apply_dictionary(text: str, doc: dict | None = None) -> str:
    """Thay các mục từ điển trong ``text`` (bỏ qua nội dung trong ``[...]``)."""
    if not text:
        return text
    data = active_doc() if doc is None else normalize_doc(doc)
    if not data.get("enabled", True):
        return text
    rules = _compile(data.get("entries") or [])
    if not rules:
        return text

    def _apply(chunk: str) -> str:
        for pattern, replacement in rules:
            chunk = pattern.sub(lambda _m, r=replacement: r, chunk)
        return chunk

    if "[" not in text:
        return _apply(text)

    out: list[str] = []
    last = 0
    for match in _RE_TAG_SPAN.finditer(text):
        out.append(_apply(text[last:match.start()]))
        out.append(match.group(0))
        last = match.end()
    out.append(_apply(text[last:]))
    return "".join(out)


# ── Nhập / xuất ──


def export_to(source: Path | str, target: Path | str) -> None:
    """Sao chép từ điển ra tệp JSON bên ngoài."""
    doc = load(Path(source))
    Path(target).write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                            encoding="utf-8")


def import_from(path: Path | str, merge: bool = False) -> dict:
    """Đọc tệp JSON bên ngoài; ``merge=False`` thay toàn bộ danh sách."""
    incoming = load(Path(path))
    if not merge:
        return incoming
    current = load()
    by_key = {
        (e["from"].casefold() if not e["case_sensitive"] else e["from"]): e
        for e in current["entries"]
    }
    for entry in incoming["entries"]:
        key = (entry["from"].casefold() if not entry["case_sensitive"]
               else entry["from"])
        by_key[key] = entry
    current["entries"] = list(by_key.values())
    return current
