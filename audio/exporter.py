from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf

# Số mẫu đọc/ghi mỗi lần khi xuất từ nguồn âm thanh trên đĩa (1 giây @48k).
_BLOCK = 48000


def export(waveform: np.ndarray, sample_rate: int, file_path: str | Path) -> Path:
    """Ghi waveform (float32 mono) ra tệp .wav hoặc .mp3."""
    path = Path(file_path)
    fmt = "MP3" if path.suffix.lower() == ".mp3" else "WAV"
    data = np.clip(np.asarray(waveform, dtype=np.float32), -1.0, 1.0)
    sf.write(str(path), data, sample_rate, format=fmt)
    return path


def export_source(source, sample_rate: int, file_path: str | Path) -> Path:
    """Ghi âm thanh từ một source (RAM hoặc đĩa) ra .wav/.mp3.

    Đọc theo block để bài dài không phải nạp toàn bộ vào RAM.
    """
    path = Path(file_path)
    is_mp3 = path.suffix.lower() == ".mp3"
    fmt = "MP3" if is_mp3 else "WAV"
    total = int(getattr(source, "total_samples", 0) or 0)
    # MP3 không dùng subtype PCM_16 -> để soundfile tự chọn.
    kwargs = {} if is_mp3 else {"subtype": "PCM_16"}
    with sf.SoundFile(str(path), "w", samplerate=int(sample_rate), channels=1,
                      format=fmt, **kwargs) as out:
        pos = 0
        while pos < total:
            block = source.read(pos, _BLOCK)
            if block is None or block.size == 0:
                break
            out.write(np.clip(block, -1.0, 1.0))
            pos += block.size
    return path
