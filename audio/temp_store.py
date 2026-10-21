"""Lưu âm thanh tổng hợp ra file tạm (PCM16) — cho bài dài, không tốn RAM.

Với bài ~2 giờ, mảng float32 trong RAM là ~1.4 GB (và bản sao thứ hai còn
nữa). TempAudioStore ghi từng câu xuống file tạm dạng PCM16 (2 byte/mẫu),
đọc lại bằng seek -> RAM gần như không đổi theo độ dài audio.

Cùng interface với GrowableBuffer (total_samples / read) nên player và
timeline dùng chung được, không cần biết đang ở chế độ nào.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import time
from pathlib import Path

import numpy as np

# Ngưỡng tự động chuyển sang chế độ đĩa (ký tự văn bản).
# ~11.7 ký tự/giây (theo thử nghiệm của CIT) -> 20.000 ký tự ≈ 28 phút.
DISK_MODE_MIN_CHARS = 20_000

_INT16_SCALE = 32767.0


class TempAudioStore:
    """Source âm thanh nằm trên đĩa, ghi tuần tự PCM16 mono.

    - append(chunk): ghi thêm mẫu, trả về tổng số mẫu đã ghi.
    - read(start, n): đọc n mẫu từ vị trí start (float32).
    - close()/cleanup(): đóng file và (tuỳ chọn) xoá thư mục session.
    """

    def __init__(self, path: str | Path, sample_rate: int) -> None:
        self.path = Path(path)
        self.sample_rate = int(sample_rate)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # 2 handle riêng: ghi và đọc. Nếu dùng chung 1 handle thì vị trí đọc
        # (seek) của player sẽ làm lệch vị trí ghi của thread tổng hợp.
        self._wfh = open(self.path, "wb")
        self._rfh = open(self.path, "rb")
        self._samples = 0
        self._closed = False

    # ── Thuộc tính ──

    @property
    def total_samples(self) -> int:
        return self._samples

    def __len__(self) -> int:
        return self._samples

    @property
    def size_bytes(self) -> int:
        return self._samples * 2

    # ── Ghi ──

    def append(self, chunk) -> None:
        if self._closed:
            return
        data = np.asarray(chunk, dtype=np.float32).reshape(-1)
        if data.size == 0:
            return
        pcm = (np.clip(data, -1.0, 1.0) * _INT16_SCALE).astype("<i2")
        self._wfh.write(pcm.tobytes())
        self._samples += int(pcm.size)

    # ── Đọc ──

    def read(self, start: int, n: int) -> np.ndarray:
        if self._closed or n <= 0:
            return np.zeros(0, dtype=np.float32)
        start = max(0, int(start))
        if start >= self._samples:
            return np.zeros(0, dtype=np.float32)
        n = min(int(n), self._samples - start)
        # Đẩy phần vừa ghi xuống đĩa để đọc được (dữ liệu còn trong buffer).
        try:
            self._wfh.flush()
        except ValueError:
            return np.zeros(0, dtype=np.float32)
        self._rfh.seek(start * 2)
        raw = self._rfh.read(n * 2)
        if not raw:
            return np.zeros(0, dtype=np.float32)
        return np.frombuffer(raw, dtype="<i2").astype(np.float32) / _INT16_SCALE

    # ── Dọn dẹp ──

    def flush(self) -> None:
        if not self._closed:
            try:
                self._wfh.flush()
            except ValueError:
                pass

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for fh in (self._wfh, self._rfh):
            try:
                fh.flush()
                fh.close()
            except Exception:
                pass

    def cleanup(self, remove_dir: bool = True) -> None:
        """Đóng file và xoá file (tuỳ chọn xoá luôn thư mục session)."""
        self.close()
        try:
            self.path.unlink(missing_ok=True)
        except OSError:
            pass
        if remove_dir:
            try:
                parent = self.path.parent
                if parent.is_dir() and not any(parent.iterdir()):
                    parent.rmdir()
            except OSError:
                pass


class TempSession:
    """Thư mục tạm cho 1 lần chuyển đổi (chứa base.pcm / play.pcm)."""

    def __init__(self, root: str | Path | None = None) -> None:
        if root is None:
            root = Path(tempfile.gettempdir()) / "phanmemtts"
        self.dir = Path(root) / f"session_{os.getpid()}_{int(time.time() * 1000)}"
        self.dir.mkdir(parents=True, exist_ok=True)
        self._stores: list[TempAudioStore] = []

    def store(self, name: str, sample_rate: int) -> TempAudioStore:
        store = TempAudioStore(self.dir / f"{name}.pcm", sample_rate)
        self._stores.append(store)
        return store

    def cleanup(self) -> None:
        # Windows không xoá được file đang mở -> đóng trước rồi mới xoá thư mục.
        for store in self._stores:
            store.close()
        self._stores.clear()
        try:
            shutil.rmtree(self.dir, ignore_errors=True)
        except Exception:
            pass


def cleanup_stale_sessions(root: str | Path | None = None,
                           max_age_hours: float = 24.0) -> int:
    """Xoá các thư mục session cũ (app bị tắt đột ngột) — trả về số đã xoá.

    Gọi 1 lần khi app khởi động.
    """
    if root is None:
        root = Path(tempfile.gettempdir()) / "phanmemtts"
    root = Path(root)
    if not root.is_dir():
        return 0
    cutoff = time.time() - max_age_hours * 3600
    removed = 0
    for folder in root.glob("session_*"):
        try:
            if folder.is_dir() and folder.stat().st_mtime < cutoff:
                shutil.rmtree(folder, ignore_errors=True)
                removed += 1
        except OSError:
            continue
    return removed


def should_use_disk(text: str, mode: str = "auto") -> bool:
    """Chọn chế độ lưu theo setting + độ dài văn bản.

    mode: "auto" (tự động theo độ dài) | "memory" | "disk"
    """
    if mode == "disk":
        return True
    if mode == "memory":
        return False
    return len(text or "") >= DISK_MODE_MIN_CHARS
