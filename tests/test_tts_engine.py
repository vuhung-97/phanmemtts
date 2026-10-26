"""Kiểm thử TtsEngine.synthesize_stream — hành vi đọc realtime (không lookahead).

Cốt lõi: generator phải yield câu đầu tiên ngay sau khi tạo xong câu đó
(không chờ câu kế), đồng thời timeline vẫn liên tục và khoảng nghỉ giữa
câu vẫn đạt chuẩn (TARGET_PAUSE_SEC).
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from engine.tts_engine import (
    GAP_SEC,
    LEAD_EST_SEC,
    TARGET_PAUSE_SEC,
    TtsEngine,
    _pause_pad_estimate,
)

SR = 48000


class FakeTTS:
    """TTS giả: sinh 1 câu dài `dur_sec`, đuôi khô (không im lặng)."""

    sample_rate = SR

    def __init__(self, dur_sec: float = 1.0) -> None:
        self.dur_sec = dur_sec
        self.calls: list[str] = []

    def generate(self, text: str, speed: float = 1.0, **kwargs):
        self.calls.append(text)
        n = int(self.dur_sec * SR)
        # Xung vuông 0.5 ở toàn bộ để đuôi/đầu KHÔNG có im lặng
        # -> mô phỏng giọng VieNeu (lead ≈ 0).
        wave = np.full(n, 0.5, dtype=np.float32)
        return SimpleNamespace(samples=wave, sample_rate=SR)


TEXT = "Câu một. Câu hai. Câu ba."


def _collect(engine: TtsEngine):
    return list(engine.synthesize_stream(TEXT, speed=1.0))


def test_yields_every_sentence():
    engine = TtsEngine(FakeTTS())
    out = _collect(engine)
    assert len(out) == 3
    assert [cur for _, _, cur, _ in out] == [1, 2, 3]
    assert [tot for _, _, _, tot in out] == [3, 3, 3]


def test_no_lookahead_first_sentence_emitted_immediately():
    """Câu đầu phải ra ngay sau 1 lần generate (không chờ câu thứ 2)."""
    tts = FakeTTS()
    engine = TtsEngine(tts)
    gen = engine.synthesize_stream(TEXT, speed=1.0)
    next(gen)
    assert len(tts.calls) == 1, "lookahead vẫn còn: câu 1 phải chờ câu 2"


def test_timeline_is_continuous():
    """start_sec câu sau = end_sec câu trước + khoảng nghỉ (pad)."""
    engine = TtsEngine(FakeTTS(dur_sec=1.0))
    out = _collect(engine)
    for i in range(len(out) - 1):
        cur = out[i][0]
        nxt = out[i + 1][0]
        assert nxt.start_sec >= cur.end_sec
        gap = nxt.start_sec - cur.end_sec
        expect = max(GAP_SEC, TARGET_PAUSE_SEC - LEAD_EST_SEC)
        assert gap == pytest.approx(expect, abs=0.02)


def test_first_sentence_starts_at_zero():
    engine = TtsEngine(FakeTTS())
    out = _collect(engine)
    assert out[0][0].start_sec == 0.0
    assert out[0][0].end_sec == pytest.approx(1.0, abs=0.01)


def test_last_sentence_has_no_trailing_pad():
    """Câu cuối không có pad ở đuôi (audio không kéo dài thêm)."""
    engine = TtsEngine(FakeTTS(dur_sec=1.0))
    out = _collect(engine)
    last_timed, last_piece, _, _ = out[-1]
    pad = max(GAP_SEC, TARGET_PAUSE_SEC - LEAD_EST_SEC)
    assert len(last_piece) == pytest.approx(1.0 * SR, rel=0.01)
    # Mốc tuyệt đối: 3 câu x 1s + 2 khoảng nghỉ
    assert last_timed.start_sec == pytest.approx(2 * (1.0 + pad), abs=0.02)
    assert last_timed.end_sec == pytest.approx(3 * 1.0 + 2 * pad, abs=0.02)


def test_piece_lengths_match_timeline():
    engine = TtsEngine(FakeTTS(dur_sec=1.0))
    out = _collect(engine)
    for timed, piece, _, _ in out:
        assert len(piece) / SR == pytest.approx(
            timed.end_sec - timed.start_sec + _pad_after(timed, out), abs=0.02)


def _pad_after(timed, out) -> float:
    """Khoảng nghỉ ngay sau câu (0 nếu là câu cuối)."""
    for i, (t, _, _, _) in enumerate(out):
        if t is timed and i < len(out) - 1:
            return out[i + 1][0].start_sec - t.end_sec
    return 0.0


def test_pause_estimate_matches_target_for_dry_tail():
    """Đuôi khô -> bù đủ khoảng nghỉ chuẩn (trừ lead ước lượng)."""
    raw = np.full(SR, 0.5, dtype=np.float32)
    pad = _pause_pad_estimate(raw, SR, GAP_SEC, TARGET_PAUSE_SEC, LEAD_EST_SEC)
    expect = max(GAP_SEC, TARGET_PAUSE_SEC - LEAD_EST_SEC)
    assert pad / SR == pytest.approx(expect, abs=0.01)


def test_pause_estimate_uses_existing_tail_silence():
    """Đuôi đã có im lặng dài -> chèn ít hơn (không dư)."""
    raw = np.concatenate([
        np.full(SR // 2, 0.5, dtype=np.float32),
        np.zeros(SR, dtype=np.float32),      # 1s im lặng ở đuôi
    ])
    pad = _pause_pad_estimate(raw, SR, GAP_SEC, TARGET_PAUSE_SEC, LEAD_EST_SEC)
    assert pad / SR == pytest.approx(GAP_SEC, abs=0.01)


# ── Thẻ trong văn bản ──

def test_pause_tag_inserts_exact_silence():
    """[nghỉ 3s] -> 1s chữ + 3s lặng + 1s chữ (câu cuối, không pad)."""
    engine = TtsEngine(FakeTTS(dur_sec=1.0))
    out = list(engine.synthesize_stream("Chờ chút [nghỉ 3s] rồi đọc.", speed=1.0))
    assert len(out) == 1
    timed, piece, _, _ = out[0]
    assert len(piece) / SR == pytest.approx(5.0, abs=0.02)
    assert timed.end_sec == pytest.approx(5.0, abs=0.02)
    middle = piece[SR + 200: 4 * SR - 200]
    assert np.max(np.abs(middle)) == pytest.approx(0.0, abs=1e-6)


def test_pause_tag_splits_model_calls():
    tts = FakeTTS(dur_sec=1.0)
    list(TtsEngine(tts).synthesize_stream("Chờ [nghỉ 2s] đọc.", speed=1.0))
    assert len(tts.calls) == 2
    assert all("[nghỉ" not in call for call in tts.calls)


def test_emotion_tag_is_passed_to_model():
    tts = FakeTTS(dur_sec=1.0)
    list(TtsEngine(tts).synthesize_stream("Xin chào [cười] bạn.", speed=1.0))
    assert any("[cười]" in call for call in tts.calls)


def test_pause_only_sentence_becomes_silence():
    """Câu chỉ có thẻ nghỉ -> 2s im lặng, không gọi model."""
    tts = FakeTTS(dur_sec=1.0)
    out = list(TtsEngine(tts).synthesize_stream("Một. [nghỉ 2s]. Hai.", speed=1.0))
    assert len(out) == 3
    _, middle_piece, _, _ = out[1]
    assert len(middle_piece) == 2 * SR
    assert np.max(np.abs(middle_piece)) == 0.0
    assert len(tts.calls) == 2
