"""Bộ đệm âm thanh tăng dần — thay cho np.concatenate lặp lại (O(n²)).

Vấn đề cũ: mỗi câu vừa tổng hợp xong lại nối vào mảng tổng bằng
np.concatenate -> copy toàn bộ mọi lần -> O(n²) về thời gian và RAM.

GrowableBuffer giữ 1 mảng float32 mono, chừa sẵn capacity và nhân đôi khi
đầy. append() chỉ copy đúng phần mới -> tổng O(n) cho cả bài.
"""

from __future__ import annotations

import numpy as np

# 1M mẫu float32 = ~4 MB — đủ cho ~21 giây audio 48 kHz.
DEFAULT_CAPACITY = 1 << 20


class GrowableBuffer:
    """Mảng float32 mono tăng dần, không copy lại toàn bộ khi append.

    Dùng như một "source" cho player:
      - total_samples : số mẫu hiện có
      - read(start, n): lấy n mẫu từ vị trí start (trả về view, không copy)
    """

    __slots__ = ("_buf", "_size")

    def __init__(self, capacity: int = DEFAULT_CAPACITY) -> None:
        self._buf = np.empty(max(1, int(capacity)), dtype=np.float32)
        self._size = 0

    # ── Thuộc tính ──

    @property
    def total_samples(self) -> int:
        return self._size

    @property
    def capacity(self) -> int:
        return int(self._buf.size)

    def __len__(self) -> int:
        return self._size

    # ── Ghi ──

    def append(self, chunk) -> None:
        """Nối chunk (float32 hoặc mảng bất kỳ) vào cuối buffer."""
        data = np.asarray(chunk, dtype=np.float32).reshape(-1)
        n = data.size
        if n == 0:
            return
        if self._size + n > self._buf.size:
            new_cap = max(self._buf.size * 2, self._size + n)
            new_buf = np.empty(new_cap, dtype=np.float32)
            new_buf[: self._size] = self._buf[: self._size]
            self._buf = new_buf
        self._buf[self._size: self._size + n] = data
        self._size += n

    def extend_from(self, other: "GrowableBuffer") -> None:
        self.append(other.view())

    # ── Đọc ──

    def view(self) -> np.ndarray:
        """View (không copy) của phần đang có dữ liệu.

        Cảnh báo: view bị vô hiệu nếu buffer được cấp phát lại (append khi
        đầy) -> luôn gọi lại view() thay vì giữ tham chiếu lâu dài.
        """
        return self._buf[: self._size]

    def read(self, start: int, n: int) -> np.ndarray:
        """Lấy tối đa n mẫu từ vị trí start (view, không copy)."""
        start = max(0, int(start))
        if start >= self._size:
            return np.zeros(0, dtype=np.float32)
        end = min(self._size, start + max(0, int(n)))
        return self._buf[start:end]

    def clear(self) -> None:
        self._size = 0
