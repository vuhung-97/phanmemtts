"""Lịch sử bản dựng — **chỉ metadata**, không sao chép file âm thanh.

Vì sao: mỗi lần xuất người dùng đã có 1 file; lưu thêm bản sao trong
``%LOCALAPPDATA%`` là thừa dung lượng. Lịch sử chỉ ghi lại thông tin và
**đường dẫn tuyệt đối** tới file gốc do người dùng chọn.

Hệ quả:

- Xoá một mục / xoá tất cả **không** xoá file âm thanh.
- File bị di chuyển/xoá → mục vẫn còn, UI đánh dấu "Thiếu file".
- Bản sao cũ (schema v1, ``audio_file`` tương đối) bị **tự xoá một lần**
  khi mở lịch sử: chỉ xoá file nằm trong thư mục ``history/`` của app.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from core.paths import data_dir

MAX_ITEMS = 200                      # số bản ghi tối đa
PREVIEW_CHARS = 80
MIGRATION_MARKER = ".migrated_v2"


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
    """Một lần xuất file — chỉ metadata, ``path`` trỏ tới file gốc."""

    id: str
    created_at: float
    voice: str
    speed: float
    duration: float
    chars: int
    preview: str
    path: str
    size: int
    legacy: bool = False      # mục schema cũ (có bản sao trong history/)

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
            "path": self.path,
            "size": self.size,
        }

    @classmethod
    def from_dict(cls, data: dict, root: Path | None = None) -> "HistoryEntry":
        if not isinstance(data, dict):
            raise ValueError("entry không hợp lệ")
        entry_id = str(data["id"])
        path = str(data.get("path") or "")
        legacy = False
        if not path:
            relative = str(data.get("audio_file") or "")
            if not relative:
                raise KeyError("path")
            path = str((root / relative) if root is not None else relative)
            legacy = True
        return cls(
            id=entry_id,
            created_at=float(data.get("created_at", 0.0)),
            voice=str(data.get("voice", "")),
            speed=float(data.get("speed", 1.0)),
            duration=float(data.get("duration", 0.0)),
            chars=int(data.get("chars", 0)),
            preview=str(data.get("preview", "")),
            path=path,
            size=int(data.get("size", 0)),
            legacy=legacy,
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

    @property
    def exists(self) -> bool:
        try:
            return bool(self.path) and Path(self.path).is_file()
        except OSError:
            return False


class HistoryStore:
    """Đọc/ghi ``index.json`` — không giữ bản sao âm thanh."""

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root) if root is not None else data_dir() / "history"
        self.index_path = self.root / "index.json"
        self.migration_summary: tuple[int, int] | None = None
        self._entries: list[HistoryEntry] = self._load()
        self._purge_legacy()

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
        if isinstance(raw, dict):
            raw = raw.get("entries")
        out: list[HistoryEntry] = []
        for item in raw if isinstance(raw, list) else []:
            try:
                out.append(HistoryEntry.from_dict(item, self.root))
            except (KeyError, TypeError, ValueError):
                continue
        out.sort(key=lambda e: e.created_at, reverse=True)
        return out

    def _save(self) -> None:
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(
                {"ver": 2, "entries": [e.to_dict() for e in self._entries]},
                ensure_ascii=False, indent=1)
            tmp = self.index_path.with_suffix(".json.tmp")
            tmp.write_text(payload, encoding="utf-8")
            tmp.replace(self.index_path)
        except OSError:
            pass

    # ── Dọn bản sao schema cũ (tự động, 1 lần) ──

    def _purge_legacy(self) -> None:
        marker = self.root / MIGRATION_MARKER
        legacy = [e for e in self._entries if e.legacy]
        if not legacy:
            if not marker.exists():
                try:
                    self.root.mkdir(parents=True, exist_ok=True)
                    marker.write_text("1", encoding="utf-8")
                except OSError:
                    pass
            return

        freed = 0
        for entry in legacy:
            path = Path(entry.path)
            if self._inside_root(path) and path.is_file():
                try:
                    freed += path.stat().st_size
                    path.unlink()
                except OSError:
                    pass
        self._entries = [e for e in self._entries if not e.legacy]
        self._cleanup_empty_dirs()
        self._save()
        try:
            marker.write_text("1", encoding="utf-8")
        except OSError:
            pass
        self.migration_summary = (len(legacy), freed)

    def _inside_root(self, path: Path) -> bool:
        try:
            return path.resolve().is_relative_to(self.root.resolve())
        except (OSError, ValueError):
            return False

    def _cleanup_empty_dirs(self) -> None:
        if not self.root.is_dir():
            return
        for folder in sorted(self.root.iterdir(), reverse=True):
            if not folder.is_dir():
                continue
            try:
                if not any(folder.iterdir()):
                    folder.rmdir()
            except OSError:
                pass

    # ── Truy vấn ──

    def audio_path(self, entry: HistoryEntry) -> Path:
        return Path(entry.path)

    def get(self, entry_id: str) -> HistoryEntry | None:
        for entry in self._entries:
            if entry.id == entry_id:
                return entry
        return None

    def total_size(self) -> int:
        return sum(max(0, e.size) for e in self._entries)

    def total_size_text(self) -> str:
        return format_size(self.total_size())

    # ── Thay đổi ──

    def add(self, audio_path: str | Path, *, voice: str = "", speed: float = 1.0,
            duration: float = 0.0, chars: int = 0,
            preview: str = "") -> HistoryEntry:
        """Ghi metadata của file vừa xuất. KHÔNG sao chép file."""
        source = Path(audio_path)
        if not source.is_file():
            raise FileNotFoundError(str(source))
        entry = HistoryEntry(
            id=time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6],
            created_at=time.time(),
            voice=str(voice or ""),
            speed=float(speed),
            duration=float(duration),
            chars=int(chars),
            preview=make_preview(preview),
            path=str(source.resolve()),
            size=source.stat().st_size,
        )
        self._entries.insert(0, entry)
        self.prune()
        self._save()
        return entry

    def remove(self, entry_id: str) -> bool:
        """Xoá khỏi danh sách — KHÔNG xoá file âm thanh."""
        entry = self.get(entry_id)
        if entry is None:
            return False
        self._entries.remove(entry)
        self._save()
        return True

    def clear(self) -> int:
        """Xoá toàn bộ danh sách — KHÔNG xoá file âm thanh."""
        count = len(self._entries)
        self._entries.clear()
        self._save()
        return count

    def prune(self, max_items: int = MAX_ITEMS) -> list[str]:
        """Bỏ bớt mục cũ nhất khi vượt số lượng — không xoá file."""
        removed: list[str] = []
        while len(self._entries) > max_items:
            oldest = self._entries.pop()
            removed.append(oldest.id)
        if removed:
            self._save()
        return removed

    # Tương thích code cũ (không còn dùng để cảnh báo dung lượng).
    def is_large(self) -> bool:
        return False

    def remove_empty_legacy_dirs(self) -> None:
        self._cleanup_empty_dirs()

    def cleanup_legacy(self) -> tuple[int, int]:
        """Dọn thủ công (dùng cho test): trả (số mục, byte)."""
        before = len(self._entries)
        self._purge_legacy()
        return self.migration_summary or (before - len(self._entries), 0)
