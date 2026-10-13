from __future__ import annotations

from math import gcd
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly


def load_audio(path: str | Path, target_sr: int = 0) -> tuple[np.ndarray, int]:
    """Đọc file .mp3/.wav → mono float32. target_sr=0 giữ nguyên sample_rate gốc."""
    data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    mono = np.mean(data, axis=1).astype(np.float32)
    if target_sr and sr != target_sr:
        g = gcd(sr, target_sr)
        mono = resample_poly(mono, target_sr // g, sr // g).astype(np.float32)
        sr = target_sr
    return mono, sr


def get_peaks(path: str | Path, num_bars: int = 200) -> tuple[np.ndarray, float]:
    """Đọc file, trả về (peaks array 0..1, total_duration_sec) — dùng vẽ waveform mini."""
    data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    mono = np.mean(data, axis=1)
    duration = len(mono) / sr if sr > 0 else 0.0
    bucket_size = max(1, len(mono) // num_bars)
    peaks = np.array([
        np.max(np.abs(mono[i:i + bucket_size]))
        for i in range(0, len(mono), bucket_size)
    ])[:num_bars]
    if peaks.max() > 0:
        peaks = peaks / peaks.max()
    return peaks.astype(np.float32), duration


def extract_segment(audio: np.ndarray, sr: int,
                    start_sec: float, end_sec: float | None) -> np.ndarray:
    """Cắt đoạn [start_sec, end_sec] từ audio. end_sec=None = đến hết."""
    start = max(0, int(start_sec * sr))
    end = int(end_sec * sr) if end_sec else len(audio)
    end = min(end, len(audio))
    if start >= end:
        return np.zeros(0, dtype=np.float32)
    return audio[start:end].copy()


def loop_to_length(audio: np.ndarray, target_samples: int) -> np.ndarray:
    """Lặp nhạc nền cho đủ target_samples."""
    if len(audio) == 0:
        return np.zeros(target_samples, dtype=np.float32)
    if len(audio) >= target_samples:
        return audio[:target_samples].copy()
    reps = int(np.ceil(target_samples / len(audio)))
    return np.tile(audio, reps)[:target_samples].astype(np.float32)


def apply_volume(audio: np.ndarray, volume: float) -> np.ndarray:
    return (audio * float(np.clip(volume, 0.0, 1.0))).astype(np.float32)


def crossfade_merge(a: np.ndarray, b: np.ndarray, fade_samples: int) -> np.ndarray:
    """Nối 2 đoạn audio với crossfade."""
    if fade_samples <= 0 or len(a) == 0 or len(b) == 0:
        return np.concatenate([a, b]).astype(np.float32)
    fade_samples = min(fade_samples, len(a), len(b))
    ramp = np.linspace(0.0, 1.0, fade_samples, dtype=np.float32)
    tail = a[-fade_samples:]
    head = b[:fade_samples]
    merged = tail * (1.0 - ramp) + head * ramp
    return np.concatenate([a[:-fade_samples], merged, b[fade_samples:]]).astype(np.float32)


def mix_background(voice: np.ndarray, bg: np.ndarray) -> np.ndarray:
    """Trộn nhạc nền chồng lên giọng đọc."""
    bg = bg[:len(voice)]
    return np.clip(voice + bg, -1.0, 1.0).astype(np.float32)


def merge(config) -> tuple[np.ndarray, int]:
    """Ghép nhạc vào file gốc. Trả về (waveform float32 mono, sample_rate)."""
    voice, sr = load_audio(config.voice_path)

    # Nhạc nền: extract segment → loop → volume
    if config.bg:
        raw, _ = load_audio(config.bg.path, target_sr=sr)
        seg = extract_segment(raw, sr, config.bg.start_sec, config.bg.end_sec)
        seg = loop_to_length(seg, len(voice))
        seg = apply_volume(seg, config.bg_volume)
        voice = mix_background(voice, seg)

    # Intro / Outro
    intro = outro = None
    if config.intro:
        raw, _ = load_audio(config.intro.path, target_sr=sr)
        intro = extract_segment(raw, sr, config.intro.start_sec, config.intro.end_sec)
        intro = apply_volume(intro, config.intro_volume)
    if config.outro:
        raw, _ = load_audio(config.outro.path, target_sr=sr)
        outro = extract_segment(raw, sr, config.outro.start_sec, config.outro.end_sec)
        outro = apply_volume(outro, config.outro_volume)

    # Nối với crossfade
    fade = int(config.crossfade_sec * sr)
    final = voice
    if intro is not None:
        final = crossfade_merge(intro, final, fade)
    if outro is not None:
        final = crossfade_merge(final, outro, fade)

    return np.clip(final, -1.0, 1.0).astype(np.float32), sr
