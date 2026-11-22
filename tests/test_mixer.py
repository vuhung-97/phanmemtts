"""Kiểm thử đọc file theo đoạn + peaks không nạp cả file (Ghép nhạc)."""

from __future__ import annotations

import numpy as np
import pytest
import soundfile as sf

from audio import mixer
from core.models import MusicMergeConfig, TrackSegment


def _write_wav(path, sr: int = 8000, seconds: float = 2.0,
               freq: float = 440.0) -> str:
    t = np.arange(int(sr * seconds), dtype=np.float32) / sr
    data = (0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    sf.write(str(path), data, sr)
    return str(path)


def test_load_segment_reads_only_range(tmp_path) -> None:
    path = _write_wav(tmp_path / "tone.wav")
    full, sr = sf.read(path, dtype="float32")

    segment, seg_sr = mixer.load_segment(path, 0.25, 0.75)

    assert seg_sr == sr
    assert len(segment) == int(0.5 * sr)
    assert np.allclose(segment, full[int(0.25 * sr):int(0.75 * sr)], atol=1e-6)


def test_load_segment_empty_range(tmp_path) -> None:
    path = _write_wav(tmp_path / "tone.wav")
    segment, sr = mixer.load_segment(path, 1.5, 1.2)
    assert len(segment) == 0
    assert sr == 8000


def test_get_peaks_does_not_need_full_read(tmp_path) -> None:
    path = _write_wav(tmp_path / "tone.wav", seconds=3.0)

    peaks, duration = mixer.get_peaks(path, num_bars=150)

    assert duration == pytest.approx(3.0, abs=0.01)
    assert len(peaks) == 150
    assert peaks.max() == pytest.approx(1.0, abs=1e-6)


def test_merge_concatenates_intro_without_crossfade(tmp_path) -> None:
    voice = _write_wav(tmp_path / "voice.wav", seconds=1.0, freq=300.0)
    intro = _write_wav(tmp_path / "intro.wav", seconds=0.5, freq=600.0)
    config = MusicMergeConfig(
        voice_paths=[voice],
        intro=TrackSegment(path=intro),
        crossfade_sec=0.0,
    )

    waveform, sr = mixer.merge(config)

    assert sr == 8000
    assert len(waveform) == int(1.5 * sr)
    assert waveform.dtype == np.float32
    assert np.max(np.abs(waveform)) <= 1.0
