from __future__ import annotations

from math import gcd
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly


def _resample(mono: np.ndarray, sr: int, target_sr: int) -> tuple[np.ndarray, int]:
    if target_sr and sr != target_sr:
        g = gcd(sr, target_sr)
        mono = resample_poly(mono, target_sr // g, sr // g).astype(np.float32)
        return mono, target_sr
    return mono, sr


def load_audio(path: str | Path, target_sr: int = 0) -> tuple[np.ndarray, int]:
    """Đọc file .mp3/.wav → mono float32. target_sr=0 giữ nguyên sample_rate gốc."""
    data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    mono = np.mean(data, axis=1).astype(np.float32)
    return _resample(mono, sr, target_sr)


def load_segment(path: str | Path, start_sec: float = 0.0,
                 end_sec: float | None = None,
                 target_sr: int = 0) -> tuple[np.ndarray, int]:
    """Chỉ đọc đoạn [start_sec, end_sec] — không nạp cả file dài vào RAM."""
    with sf.SoundFile(str(path)) as handle:
        sr = int(handle.samplerate)
        total = int(handle.frames)
        start = max(0, int(float(start_sec) * sr))
        end = total if end_sec is None else min(total, int(float(end_sec) * sr))
        if start >= end:
            return np.zeros(0, dtype=np.float32), (target_sr or sr)
        handle.seek(start)
        data = handle.read(end - start, dtype="float32", always_2d=True)
    mono = np.mean(data, axis=1).astype(np.float32) if len(data) else np.zeros(
        0, dtype=np.float32)
    return _resample(mono, sr, target_sr)


def get_peaks(path: str | Path, num_bars: int = 200) -> tuple[np.ndarray, float]:
    """Peaks 0..1 + thời lượng — đọc từng block nhỏ, không nạp cả file."""
    num_bars = max(1, int(num_bars))
    try:
        with sf.SoundFile(str(path)) as handle:
            sr = int(handle.samplerate)
            total = int(handle.frames)
            duration = total / sr if sr > 0 else 0.0
            if total <= 0:
                return np.zeros(0, dtype=np.float32), duration
            bucket = max(1, total // num_bars)
            span = max(1, min(bucket, 2048))
            count = min(num_bars, max(1, total // bucket))
            peaks = np.zeros(count, dtype=np.float32)
            for i in range(count):
                handle.seek(i * bucket + max(0, (bucket - span) // 2))
                data = handle.read(span, dtype="float32", always_2d=True)
                if len(data):
                    peaks[i] = float(np.max(np.abs(np.mean(data, axis=1))))
    except Exception:
        # File lạ không seek được -> đọc cả file (chấp nhận tốn RAM).
        data, sr = sf.read(str(path), dtype="float32", always_2d=True)
        mono = np.mean(data, axis=1)
        duration = len(mono) / sr if sr > 0 else 0.0
        bucket = max(1, len(mono) // num_bars)
        peaks = np.array([
            np.max(np.abs(mono[i:i + bucket]))
            for i in range(0, len(mono), bucket)
        ])[:num_bars].astype(np.float32)
    if peaks.size and peaks.max() > 0:
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
    """Ghép nhạc vào file gốc. Trả về (waveform float32 mono, sample_rate).

    config.voice_paths: nhiều đoạn giọng đọc được nối theo thứ tự
    (resample về sample_rate của đoạn đầu).
    """
    if not config.voice_paths:
        raise ValueError("Chưa chọn file gốc.")

    # Nối các file giọng: gom list rồi concatenate MỘT lần (tránh O(n²)).
    first, sr = load_audio(config.voice_paths[0])
    parts = [first]
    for path in config.voice_paths[1:]:
        seg, _ = load_audio(path, target_sr=sr)
        parts.append(seg)
    voice = parts[0] if len(parts) == 1 else np.concatenate(parts)
    parts.clear()

    # Nhạc nền: chỉ đọc đúng đoạn cần → loop → volume, trộn tại chỗ.
    if config.bg:
        seg, _ = load_segment(config.bg.path, config.bg.start_sec,
                              config.bg.end_sec, target_sr=sr)
        seg = loop_to_length(seg, len(voice))
        seg = apply_volume(seg, config.bg_volume)
        np.add(voice, seg[:len(voice)], out=voice)
        np.clip(voice, -1.0, 1.0, out=voice)
        del seg

    # Intro / Outro: cũng chỉ đọc đúng đoạn cần.
    intro = outro = None
    if config.intro:
        intro, _ = load_segment(config.intro.path, config.intro.start_sec,
                                config.intro.end_sec, target_sr=sr)
        intro = apply_volume(intro, config.intro_volume)
    if config.outro:
        outro, _ = load_segment(config.outro.path, config.outro.start_sec,
                                config.outro.end_sec, target_sr=sr)
        outro = apply_volume(outro, config.outro_volume)

    # Nối với crossfade
    fade = int(config.crossfade_sec * sr)
    final = voice
    if intro is not None:
        final = crossfade_merge(intro, final, fade)
    if outro is not None:
        final = crossfade_merge(final, outro, fade)

    final = np.asarray(final, dtype=np.float32)
    np.clip(final, -1.0, 1.0, out=final)
    return final, sr
