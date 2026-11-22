"""Kiểm thử các biện pháp chống tăng RAM.

- Đổi giọng cùng engine chỉ gọi set_voice (không nạp lại model).
- unload gọi close() để trả session ONNX.
- Player/source giải phóng được audio.
- compute_peaks chỉ đọc mẫu thưa (không quét toàn bộ audio).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

import engine.model_manager as model_manager
from audio.buffer import GrowableBuffer
from audio.peaks import compute_peaks
from audio.player import AudioPlayer
from core.models import VoiceModelInfo


def _info(model_id: str) -> VoiceModelInfo:
    marker = Path("models/vieneu/voice.json")
    return VoiceModelInfo(
        model_id=model_id,
        display_name=model_id.split(":", 1)[-1],
        language="vi",
        model_path=marker,
        config_path=marker,
        tokens_path=marker,
        data_dir=Path("models/vieneu"),
        engine="vieneu",
    )


class FakeTTS:
    def __init__(self, voice: str) -> None:
        self.voice = voice
        self.set_calls: list[str] = []
        self.closed = False

    def set_voice(self, model_id: str) -> None:
        self.set_calls.append(model_id)
        self.voice = model_id

    def close(self) -> None:
        self.closed = True


def test_voice_switch_reuses_model(monkeypatch) -> None:
    builds: list[str] = []

    def fake_build(info, precision, threads, low_memory=False):
        builds.append(info.model_id)
        return FakeTTS(info.model_id)

    monkeypatch.setattr(model_manager, "_build_tts", fake_build)
    mm = model_manager.ModelManager(onnx_memory="off")

    first = mm.load_tts(_info("vieneu:Hải Đăng"))
    second = mm.load_tts(_info("vieneu:Trúc Ly"))

    assert first is second
    assert builds == ["vieneu:Hải Đăng"]
    assert second.set_calls == ["vieneu:Trúc Ly"]


def test_refresh_custom_voices_does_not_reload_model(monkeypatch) -> None:
    builds: list[str] = []

    class RefreshTTS(FakeTTS):
        def __init__(self, voice: str) -> None:
            super().__init__(voice)
            self.refreshed = 0

        def refresh_custom_voices(self) -> None:
            self.refreshed += 1

    def fake_build(info, precision, threads, low_memory=False):
        builds.append(info.model_id)
        return RefreshTTS(info.model_id)

    monkeypatch.setattr(model_manager, "_build_tts", fake_build)
    mm = model_manager.ModelManager(onnx_memory="off")
    tts = mm.load_tts(_info("vieneu:Hải Đăng"))

    mm.refresh_custom_voices()

    assert tts.refreshed == 1
    assert builds == ["vieneu:Hải Đăng"]


def test_unload_closes_engine(monkeypatch) -> None:
    def fake_build(info, precision, threads, low_memory=False):
        return FakeTTS(info.model_id)

    monkeypatch.setattr(model_manager, "_build_tts", fake_build)
    mm = model_manager.ModelManager(onnx_memory="off")
    tts = mm.load_tts(_info("vieneu:Hải Đăng"))
    mm.unload()

    assert tts.closed is True
    assert mm._loaded_tts is None


def test_growable_buffer_cleanup_releases_capacity() -> None:
    buf = GrowableBuffer(capacity=1024)
    buf.append(np.ones(1024, dtype=np.float32))
    assert buf.total_samples == 1024

    buf.cleanup()

    assert buf.total_samples == 0
    assert buf.capacity == 1


def test_player_release_source_drops_audio() -> None:
    player = AudioPlayer()
    player._available = False           # không mở thiết bị âm thanh khi test
    player.load(np.ones(2048, dtype=np.float32), 48000)

    assert player._source is not None
    player.release_source()

    assert player._source is None
    assert player._sample_rate == 0
    assert player.get_position() == 0.0


class _CountingSource:
    def __init__(self, total: int) -> None:
        self.total_samples = total
        self.samples_read = 0

    def read(self, start: int, n: int) -> np.ndarray:
        n = max(0, min(int(n), self.total_samples - int(start)))
        self.samples_read += n
        return np.ones(n, dtype=np.float32)


def test_peaks_reads_sampled_not_whole_audio() -> None:
    source = _CountingSource(10_000_000)

    peaks = compute_peaks(source, num_bars=300)

    assert len(peaks) == 300
    # 300 thanh × 2048 mẫu, không phải 10 triệu mẫu.
    assert source.samples_read <= 300 * 2048
    assert np.all(peaks >= 0.99)
