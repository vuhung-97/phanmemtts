from __future__ import annotations

import numpy as np


def apply_speed(samples: np.ndarray, speed: float) -> np.ndarray:
    """Time-stretch giữ cao độ — model VieNeu không có knob speed nên áp ở đây.

    speed > 1 → đọc nhanh, speed < 1 → đọc chậm. Fail-safe: giữ audio gốc nếu lỗi.
    """
    if abs(speed - 1.0) < 0.01 or len(samples) < 1024:
        return samples
    try:
        from librosa import effects
        out = effects.time_stretch(np.asarray(samples, dtype=np.float32),
                                   rate=float(speed))
        return np.asarray(out, dtype=np.float32)
    except Exception:
        return samples
