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


# Số mẫu đọc cho mỗi thanh waveform. Waveform chỉ để hiển thị nên không cần
# quét toàn bộ audio (bài dài 20k ký tự ~320 MB -> trước đây quét lại toàn bộ
# mỗi 0,4 giây, vừa chậm vừa tạo áp lực bộ nhớ).
SAMPLES_PER_BAR = 2048


def compute_peaks(source, num_bars: int = 300,
                  samples_per_bar: int = SAMPLES_PER_BAR) -> np.ndarray:
    """Trả về peaks 0..1, mỗi phần tử là max(|mẫu|) trong 1 bucket.

    Mỗi bucket chỉ đọc tối đa ``samples_per_bar`` mẫu ở giữa bucket -> chi phí
    O(num_bars × samples_per_bar), không phụ thuộc độ dài audio.
    """
    total = _total_samples(source)
    if total <= 0:
        return np.zeros(0, dtype=np.float32)
    num_bars = max(1, int(num_bars))
    bucket = max(1, total // num_bars)
    count = min(num_bars, max(1, total // bucket))
    span = max(1, min(bucket, int(samples_per_bar)))
    peaks = np.zeros(count, dtype=np.float32)
    for i in range(count):
        start = i * bucket + max(0, (bucket - span) // 2)
        seg = _read(source, start, min(span, total - start))
        if seg is not None and seg.size:
            peaks[i] = float(np.max(np.abs(seg)))
    peak_max = float(peaks.max()) if peaks.size else 0.0
    if peak_max > 0:
        peaks /= peak_max
    return peaks
