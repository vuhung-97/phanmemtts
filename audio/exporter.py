from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf


def export(waveform: np.ndarray, sample_rate: int, file_path: str | Path) -> Path:
    """Ghi waveform (float32 mono) ra tệp .wav hoặc .mp3."""
    path = Path(file_path)
    fmt = "MP3" if path.suffix.lower() == ".mp3" else "WAV"
    data = np.clip(np.asarray(waveform, dtype=np.float32), -1.0, 1.0)
    sf.write(str(path), data, sample_rate, format=fmt)
    return path
