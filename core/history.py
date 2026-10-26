"""Lịch sử bản dựng audio — bền vững trên đĩa.

Cấu trúc (mặc định trong ``data_dir()/history``)::

    index.json              # danh sách bản ghi, mới nhất trước
    <id>/audio.mp3          # bản SAO của file đã xuất

Vì sao phải sao chép: người dùng thường xuất ra Desktop/USB rồi xoá file gốc;
lịch sử phải còn nghe lại được. Xoá một mục trong lịch sử chỉ xoá bản sao,
không đụng file người dùng đã xuất.

Mọi lỗi đọc/ghi đều được nuốt (trả danh sách rỗng / bỏ qua) vì lịch sử là
tính năng phụ — không được làm hỏng luồng xuất file chính.
"""

from __future__ import annotations

import json
import shutil
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from core.paths import data_dir

MAX_ITEMS = 200                      # số bản ghi tối đa
WARN_BYTES = 500 * 1024 * 1024       # 500 MB -> UI cảnh báo
PRUNE_BYTES = 1024 * 1024 * 1024     # 1 GB -> tự xoá bản cũ nhất
PREVIEW_CHARS = 80


def format_size(size: int) -> str:
    size = max(0, int(size))
    if size >= 1024 ** 3:
        return f"{size / 1024 ** 3:.2f} GB"
    if size >= 1024 ** 2:
        return f"{size / 1024 ** 2:.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.0f} KB"
    return f"{size} B"


def format_duration(seconds: float) -> str:
    total = int(round(max(0.0, float(seconds))))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def make_preview(text: str, limit: int = PREVIEW_CHARS) -> str:
    clean = " ".join((text or "").split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "…"


@dataclass
class HistoryEntry:
    """Một lần xuất file thành công."""

    id: str
    created_at: float
    voice: str
    speed: float
    duration: float
    chars: int
    preview: str
    audio_file: str          # đường dẫn tương đối trong thư mục lịch sử
    size: int

    # ── JSON ──

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "voice": self.voice,
            "speed": self.speed,
            "duration": self.duration,
            "chars": self.chars,
            "preview": self.preview,
            "audio_file": self.audio_file,
            "size": self.size,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "HistoryEntry":
        return cls(
            id=str(data["id"]),
            created_at=float(data.get("created_at", 0.0)),
            voice=str(data.get("voice", "")),
            speed=float(data.get("speed", 1.0)),
            duration=float(data.get("duration", 0.0)),
            chars=int(data.get("chars", 0)),
            preview=str(data.get("preview", "")),
            audio_file=str(data["audio_file"]),
            size=int(data.get("size", 0)),
        )

    # ── Hiển thị ──

    @property
    def created_text(self) -> str:
        try:
            return time.strftime("%d/%m/%Y %H:%M", time.localtime(self.created_at))
        except (OSError, ValueError):
            return "—"

    @property
    def duration_text(self) -> str:
        return format_duration(self.duration)

    @property
    def size_text(self) -> str:
        return format_size(self.size)

    @property
    def speed_text(self) -> str:
        return f"{self.speed:g}x"


class HistoryStore:
    """Đọc/ghi ``index.json`` + các thư mục con chứa bản sao audio."""

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root) if root is not None else data_dir() / "history"
        self.index_path = self.root / "index.json"
        self._entries: list[HistoryEntry] = self._load()

    # ── Đọc / ghi ──

    @property
    def entries(self) -> list[HistoryEntry]:
        return list(self._entries)

    def _load(self) -> list[HistoryEntry]:
        if not self.index_path.exists():
            return []
        try:
            raw = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        out: list[HistoryEntry] = []
        for item in raw if isinstance(raw, list) else []:
            try:
                out.append(HistoryEntry.from_dict(item))
            except (KeyError, TypeError, ValueError):
                continue
        out.sort(key=lambda e: e.created_at, reverse=True)
        return out

    def _save(self) -> None:
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            payload = json.dumps([e.to_dict() for e in self._entries],
                                 ensure_ascii=False, indent=1)
            tmp = self.index_path.with_suffix(".json.tmp")
            tmp.write_text(payload, encoding="utf-8")
            tmp.replace(self.index_path)
        except OSError:
            pass

    # ── Truy vấn ──

    def audio_path(self, entry: HistoryEntry) -> Path:
        return self.root / entry.audio_file

    def get(self, entry_id: str) -> HistoryEntry | None:
        for entry in self._entries:
            if entry.id == entry_id:
                return entry
        return None

    def total_size(self) -> int:
        return sum(max(0, e.size) for e in self._entries)

    def total_size_text(self) -> str:
        return format_size(self.total_size())

    def is_large(self) -> bool:
        return self.total_size() >= WARN_BYTES

    # ── Thay đổi ──

    def add(self, audio_path: str | Path, *, voice: str = "", speed: float = 1.0,
            duration: float = 0.0, chars: int = 0, preview: str = "") -> HistoryEntry:
        """Sao chép file vừa xuất vào lịch sử và ghi index."""
        source = Path(audio_path)
        entry_id = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
        folder = self.root / entry_id
        folder.mkdir(parents=True, exist_ok=True)
        name = f"audio{source.suffix.lower() or '.mp3'}"
        dest = folder / name
        shutil.copy2(source, dest)
        entry = HistoryEntry(
            id=entry_id,
            created_at=time.time(),
            voice=str(voice or ""),
            speed=float(speed),
            duration=float(duration),
            chars=int(chars),
            preview=make_preview(preview),
            audio_file=f"{entry_id}/{name}",
            size=dest.stat().st_size,
        )
        self._entries.insert(0, entry)
        self.prune()
        self._save()
        return entry

    def remove(self, entry_id: str) -> bool:
        entry = self.get(entry_id)
        if entry is None:
            return False
        self._entries.remove(entry)
        self._delete_files(entry)
        self._save()
        return True

    def clear(self) -> int:
        count = len(self._entries)
        for entry in self._entries:
            self._delete_files(entry)
        self._entries.clear()
        self._save()
        return count

    def prune(self, max_items: int = MAX_ITEMS,
              max_bytes: int = PRUNE_BYTES) -> list[str]:
        """Xoá bản cũ nhất cho tới khi đủ giới hạn. Trả về id đã xoá."""
        removed: list[str] = []
        while self._entries and (
            len(self._entries) > max_items or self.total_size() > max_bytes
        ):
            oldest = self._entries.pop()          # cuối danh sách = cũ nhất
            self._delete_files(oldest)
            removed.append(oldest.id)
        return removed

    def _delete_files(self, entry: HistoryEntry) -> None:
        folder = (self.root / entry.audio_file).parent
        try:
            if folder != self.root and folder.exists():
                shutil.rmtree(folder, ignore_errors=True)
        except OSError:
            pass
