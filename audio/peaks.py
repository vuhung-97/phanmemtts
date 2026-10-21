"""Tính đường viền sóng (peaks) từ một source âm thanh bất kỳ.

Source = object có .total_samples và .read(start, n) — dùng chung cho
GrowableBuffer (RAM) và TempAudioStore (đĩa) nên timeline vẽ được ở cả
hai chế độ mà không cần copy toàn bộ mảng.

Hàm cũng nhận mảng numpy thuần (đã nằm trong RAM).
"""

from __future__ import annotations

import numpy as np


def _total_samples(source) -> int:
    if hasattr(source, "total_samples"):
        return int(source.total_samples or 0)
    try:
        return int(len(source))
    except TypeError:
        return 0


def _read(source, start: int, n: int) -> np.ndarray:
    read = getattr(source, "read", None)
    if callable(read):
        return read(start, n)
    return np.asarray(source[start:start + n], dtype=np.float32)


def compute_peaks(source, num_bars: int = 300) -> np.ndarray:
    """Trả về mảng peaks 0..1, mỗi phần tử là max(|mẫu|) trong 1 bucket."""
    total = _total_samples(source)
    if total <= 0:
        return np.zeros(0, dtype=np.float32)
    num_bars = max(1, int(num_bars))
    bucket = max(1, total // num_bars)
    count = min(num_bars, max(1, total // bucket))
    peaks = np.zeros(count, dtype=np.float32)
    for i in range(count):
        start = i * bucket
        seg = _read(source, start, min(bucket, total - start))
        if seg is not None and seg.size:
            peaks[i] = float(np.max(np.abs(seg)))
    peak_max = float(peaks.max()) if peaks.size else 0.0
    if peak_max > 0:
        peaks /= peak_max
    return peaks
