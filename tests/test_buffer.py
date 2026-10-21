"""Kiểm thử GrowableBuffer — thay thế O(n²) của np.concatenate."""

from __future__ import annotations

import numpy as np

from audio.buffer import GrowableBuffer


def test_append_accumulates_samples():
    buf = GrowableBuffer(capacity=4)
    buf.append(np.ones(3, dtype=np.float32))
    buf.append(np.full(5, 2.0, dtype=np.float32))
    assert buf.total_samples == 8
    assert len(buf) == 8
    data = buf.view()
    assert data.shape == (8,)
    assert data[0] == 1.0 and data[-1] == 2.0


def test_growth_beyond_capacity_keeps_data():
    buf = GrowableBuffer(capacity=2)
    for i in range(10):
        buf.append(np.full(3, float(i), dtype=np.float32))
    assert buf.total_samples == 30
    data = buf.view()
    assert np.allclose(data[:3], 0.0)
    assert np.allclose(data[27:], 9.0)


def test_read_returns_slice_without_copy():
    buf = GrowableBuffer()
    buf.append(np.arange(10, dtype=np.float32))
    seg = buf.read(3, 4)
    assert seg.tolist() == [3.0, 4.0, 5.0, 6.0]
    # Vượt cuối -> trả về phần còn lại
    assert buf.read(8, 10).tolist() == [8.0, 9.0]
    # Ngoài phạm vi -> rỗng
    assert buf.read(20, 5).size == 0


def test_clear_resets_size():
    buf = GrowableBuffer()
    buf.append(np.ones(10, dtype=np.float32))
    buf.clear()
    assert buf.total_samples == 0
    assert buf.view().size == 0
