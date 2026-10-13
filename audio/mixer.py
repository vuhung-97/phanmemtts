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

    # Nhạc nền: loop + volume
    if config.bg_path:
        bg, _ = load_audio(config.bg_path, target_sr=sr)
        bg = loop_to_length(bg, len(voice))
        bg = apply_volume(bg, config.bg_volume)
        voice = mix_background(voice, bg)

    # Intro / Outro
    intro = outro = None
    if config.intro_path:
        intro, _ = load_audio(config.intro_path, target_sr=sr)
        intro = apply_volume(intro, config.intro_volume)
    if config.outro_path:
        outro, _ = load_audio(config.outro_path, target_sr=sr)
        outro = apply_volume(outro, config.outro_volume)

    # Nối với crossfade
    fade = int(config.crossfade_sec * sr)
    final = voice
    if intro is not None:
        final = crossfade_merge(intro, final, fade)
    if outro is not None:
        final = crossfade_merge(final, outro, fade)

    return np.clip(final, -1.0, 1.0).astype(np.float32), sr
