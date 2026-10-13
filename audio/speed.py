from __future__ import annotations

import numpy as np

# Ngưỡng coi là "đang có tiếng" khi đo RMS (loại khoảng im, vì tỉ lệ im
# thay đổi theo speed — tính cả im sẽ ra gain sai).
_ACTIVE_EPS = 1e-4
_GAIN_MIN = 0.5
_GAIN_MAX = 4.0
_PEAK_MAX = 0.98


def _active_rms(y: np.ndarray) -> float:
    mask = np.abs(y) > _ACTIVE_EPS
    if not mask.any():
        return 0.0
    return float(np.sqrt(np.mean(y[mask] ** 2)))


def apply_speed(samples: np.ndarray, speed: float) -> np.ndarray:
    """Time-stretch giữ cao độ — model VieNeu không có knob speed nên áp ở đây.

    speed > 1 → đọc nhanh, speed < 1 → đọc chậm.
    Sau stretch, bù gain để âm lượng (RMS đoạn có tiếng) bằng bản gốc —
    phase-vocoder làm âm nhỏ đi tới ~4.5dB ở speed cao.
    Fail-safe: giữ audio gốc nếu lỗi.
    """
    if abs(speed - 1.0) < 0.01 or len(samples) < 1024:
        return samples
    try:
        from librosa import effects

        x = np.asarray(samples, dtype=np.float32)
        rms_before = _active_rms(x)
        y = np.asarray(effects.time_stretch(x, rate=float(speed)),
                       dtype=np.float32)

        rms_after = _active_rms(y)
        if rms_before > 0 and rms_after > 0:
            gain = float(np.clip(rms_before / rms_after, _GAIN_MIN, _GAIN_MAX))
            y = y * gain
            peak = float(np.max(np.abs(y))) if len(y) else 0.0
            if peak > _PEAK_MAX:
                y = y * (_PEAK_MAX / peak)
        return y.astype(np.float32)
    except Exception:
        return samples   # fail-safe: giữ audio gốc, không crash export
