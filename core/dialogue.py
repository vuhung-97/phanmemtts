"""Kịch bản hội thoại nhiều giọng: ``Tên nhân vật: nội dung``.

Quy tắc:

- Mỗi dòng (không rỗng, không bắt đầu ``#``) phải có dạng ``Tên: nội dung``.
- Thiếu tên/nội dung → **lỗi chặn**, kèm số dòng để UI nhảy tới.
- Tên tối đa 40 ký tự, không chứa ``[`` ``]`` (tránh nhầm với thẻ).
- Tên trùng (khác hoa/thường) gộp về một nhân vật, chỉ cảnh báo.

Phụ trợ:

- ``dialogue_cast.json`` (nội bộ) nhớ giọng từng nhân vật theo **tên**.
- ``dialogue_draft.txt`` tự lưu nháp kịch bản — người dùng không phải quản lý file.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from core.paths import data_dir

CAST_FILENAME = "dialogue_cast.json"
DRAFT_FILENAME = "dialogue_draft.txt"
MAX_SPEAKER_LEN = 40

_RE_LINE = re.compile(r"^\s*([^:\n]{1,80}?)\s*:\s*(.*)$")


@dataclass(frozen=True)
class DialogueIssue:
    """Một lỗi trong kịch bản (chặn tạo hội thoại)."""

    line_no: int
    message: str

    def __str__(self) -> str:
        return f"Dòng {self.line_no}: {self.message}" if self.line_no else self.message


@dataclass(frozen=True)
class DialogueTurn:
    """Một lượt nói; ``char_start/char_end`` trỏ vào phần nội dung trong kịch bản."""

    speaker: str
    text: str
    line_no: int
    char_start: int
    char_end: int


@dataclass
class DialogueScript:
    turns: list[DialogueTurn] = field(default_factory=list)
    speakers: list[str] = field(default_factory=list)
    issues: list[DialogueIssue] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.turns) and not self.issues

    def turns_of(self, speaker: str) -> int:
        return sum(1 for turn in self.turns if turn.speaker == speaker)


def parse_script(text: str) -> DialogueScript:
    """Tách kịch bản thành lượt nói + lỗi/cảnh báo."""
    script = DialogueScript()
    if not text or not text.strip():
        script.issues.append(DialogueIssue(0, "Kịch bản trống."))
        return script

    canonical: dict[str, str] = {}
    offset = 0
    for line_no, raw in enumerate(text.splitlines(keepends=True), start=1):
        body = raw.rstrip("\r\n")
        stripped = body.strip()
        if not stripped or stripped.startswith("#"):
            offset += len(raw)
            continue

        match = _RE_LINE.match(body)
        if match is None:
            script.issues.append(DialogueIssue(
                line_no, "thiếu 'Tên:' ở đầu dòng."))
            offset += len(raw)
            continue

        name = match.group(1).strip()
        content = match.group(2).strip()
        if not name:
            script.issues.append(DialogueIssue(line_no, "thiếu tên nhân vật."))
        elif len(name) > MAX_SPEAKER_LEN:
            script.issues.append(DialogueIssue(
                line_no, f"tên nhân vật quá dài (tối đa {MAX_SPEAKER_LEN} ký tự)."))
        elif "[" in name or "]" in name:
            script.issues.append(DialogueIssue(
                line_no, "tên nhân vật không được chứa '[' hoặc ']'."))
        if not content:
            script.issues.append(DialogueIssue(
                line_no, "thiếu nội dung sau dấu ':'."))

        if name and content:
            key = name.casefold()
            if key not in canonical:
                canonical[key] = name
                script.speakers.append(name)
            else:
                speaker = canonical[key]
                if speaker != name:
                    script.warnings.append(
                        f"Dòng {line_no}: '{name}' được gộp vào '{speaker}'.")
                name = speaker
            char_start = offset + match.start(2)
            script.turns.append(DialogueTurn(
                speaker=name, text=content, line_no=line_no,
                char_start=char_start, char_end=char_start + len(content)))

        offset += len(raw)

    if not script.turns and not script.issues:
        script.issues.append(DialogueIssue(0, "Kịch bản không có lượt nói nào."))
    return script


# ── Nhớ giọng theo tên nhân vật ──


def cast_path() -> Path:
    return data_dir() / CAST_FILENAME


def load_cast() -> dict[str, str]:
    """Trả ``{tên nhân vật: model_id}``; file hỏng → rỗng."""
    try:
        data = json.loads(cast_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    cast = data.get("cast") if isinstance(data, dict) else None
    if not isinstance(cast, dict):
        return {}
    return {str(name): str(model_id) for name, model_id in cast.items()
            if isinstance(model_id, str) and model_id}


def save_cast(cast: dict[str, str]) -> None:
    path = cast_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"ver": 1,
                   "cast": {name: model_id for name, model_id in cast.items()
                            if model_id}}
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        tmp.replace(path)
    except OSError:
        pass


# ── Nháp kịch bản ──


def draft_path() -> Path:
    return data_dir() / DRAFT_FILENAME


def load_draft() -> str:
    try:
        return draft_path().read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def save_draft(text: str) -> None:
    try:
        path = draft_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text or "", encoding="utf-8")
    except OSError:
        pass


#: Kịch bản mẫu để người dùng thấy cách viết ngay.
SAMPLE_SCRIPT = """# Bản tin phát thanh — thay nội dung của bạn
An: Xin chào, tôi là An.
Bình: Chào An. Hôm nay có gì mới?
An: [nghỉ 1s] Có ba tin đáng chú ý trong buổi phát thanh hôm nay.
Bình: Mời anh đọc tin đầu tiên.
"""
