from __future__ import annotations

from typing import Iterator

import numpy as np

from core.models import SentenceItem, TimelineMap
from core.text_normalizer import normalize_numbers_vi
from core.text_processor import build_sentences

GAP_SEC = 0.25            # sàn tạm ngủ giữa 2 câu (giữ nhịp app hiện tại)
TARGET_PAUSE_SEC = 0.5    # khoảng nghỉ thật chuẩn "sentence" của VieNeu (V3_GAP_SILENCE)
FADE_SEC = 0.03           # fade cosine 2 mép câu -> không cut thô (chống "ghép 2 đoạn")
EDGE_THRESH_DB = -45.0    # đồng chuẩn vieneu_utils.edge_silence
EDGE_WIN_S = 0.01
SILENCE_SAMPLE_RATE = 22050
_TERMINAL_CHARS = ".?!…"
_SPECIAL_QUOTES = {
    "“": '"', "”": '"', "„": '"', "‟": '"',
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
    "–": "-", "—": "-", "…": "...",
}


def _edge_silence(wav: np.ndarray, sr: int) -> tuple[int, int]:
    """(lead, tail): số mẫu im lặng ở đầu/cuối — cửa sổ 10ms, ngưỡng -45dB.

    Bản sao logic vieneu_utils.edge_silence để tts_engine không phụ thuộc SDK.
    """
    n = int(wav.size)
    win = max(1, int(EDGE_WIN_S * sr))
    n_win = n // win
    if n_win == 0:
        return n, 0
    env = np.abs(wav[: n_win * win]).reshape(n_win, win).mean(1)
    above = np.flatnonzero(env > 10 ** (EDGE_THRESH_DB / 20))
    if not above.size:
        return n, 0  # toàn im lặng
    lead = int(above[0]) * win
    tail = n - (int(above[-1]) + 1) * win
    return lead, tail


def _pause_pad_samples(prev_raw: np.ndarray, next_raw: np.ndarray, sr: int,
                       gap_sec: float, target_sec: float) -> int:
    """Số mẫu zeros cần chèn giữa 2 câu để nghỉ thật đạt max(gap_sec, target_sec).

    Đuôi/đầu im lặng sẵn đã đủ -> chèn đúng gap_sec như nhịp cũ (preset không đổi).
    Đuôi khô (giọng clone) -> bù thêm cho đủ target_sec (chuẩn sentence của VieNeu).
    """
    lead_prev, tail = _edge_silence(prev_raw, sr)
    if lead_prev == prev_raw.size:
        tail = prev_raw.size
    lead, _ = _edge_silence(next_raw, sr)
    have = (tail + lead) / sr
    need = max(gap_sec, target_sec - have)
    return max(0, int(need * sr))


def _fade_edges(samples: np.ndarray, sr: int) -> np.ndarray:
    """Fade cosine FADE_SEC ở 2 mép -> chuyển tiếp sang zeros/âm khác không cut thô."""
    n = min(int(FADE_SEC * sr), len(samples) // 2)
    if n <= 0:
        return samples
    out = samples.copy()
    ramp = (0.5 - 0.5 * np.cos(np.linspace(0.0, np.pi, n))).astype(np.float32)
    out[:n] *= ramp
    out[-n:] *= ramp[::-1]
    return out


def prepare_for_tts(text: str) -> str:
    """Chuẩn hóa câu trước khi đưa vào mô hình (chống nhại, đọc số thành chữ)."""
    for src, dst in _SPECIAL_QUOTES.items():
        text = text.replace(src, dst)
    text = normalize_numbers_vi(text.strip())
    if not text:
        return text
    if text[-1] not in _TERMINAL_CHARS:
        text += "."
    return text


class TtsEngine:
    """Tổng hợp âm thanh theo từng câu và dựng TimelineMap (hỗ trợ cả batch và stream)."""

    def __init__(self, tts) -> None:
        self.tts = tts

    @property
    def sample_rate(self) -> int:
        return int(self.tts.sample_rate)

    def synthesize(self, text: str, speed: float = 1.0,
                   progress_callback=None) -> tuple[np.ndarray, TimelineMap]:
        pieces: list[np.ndarray] = []
        timeline = TimelineMap(sentences=[], sample_rate=self.sample_rate)
        for timed, piece, cur, tot in self.synthesize_stream(text, speed=speed):
            pieces.append(piece)
            timeline.sentences.append(timed)
            if progress_callback is not None:
                progress_callback(cur, tot)
        waveform = np.concatenate(pieces) if pieces else np.zeros(0, dtype=np.float32)
        return waveform, timeline

    def synthesize_stream(
        self, text: str, speed: float = 1.0
    ) -> Iterator[tuple[SentenceItem, np.ndarray, int, int]]:
        """Generator trả về từng câu (nối kiểu pause-pad, trễ 1 câu để biết số kế):

        - Fade cosine FADE_SEC ở 2 mép mỗi câu -> hết cut thô ("ghép 2 đoạn").
        - Chèn zeros giữa câu i và i+1 sao cho nghỉ THẬT đạt
          max(GAP_SEC, TARGET_PAUSE_SEC - im lặng có sẵn): giọng đuôi dài
          (preset) giữ nguyên nhịp cũ, giọng đuôi khô (clone) được bù đủ.
        - Timeline: end_sec = hết tiếng (không tính pad), start_sec câu sau
          tính từ sau pad — công thức như bản cũ, chỉ thay gap cố định.

        yields: (SentenceItem, piece_waveform, current_idx_1based, total_sentences)
        """
        sentences = build_sentences(text)
        if not sentences:
            return

        sr = self.sample_rate
        speed_factor = max(speed, 0.1)
        gap_sec = GAP_SEC / speed_factor
        target_sec = TARGET_PAUSE_SEC / speed_factor
        cursor_samples = 0
        total = len(sentences)

        def make_timed(sentence: SentenceItem, start_sec: float,
                       end_sec: float) -> SentenceItem:
            return SentenceItem(
                index=sentence.index,
                text=sentence.text,
                char_start=sentence.char_start,
                char_end=sentence.char_end,
                start_sec=start_sec,
                end_sec=max(end_sec, start_sec),
            )

        # pending = (faded, raw, sentence, idx 0-based) — giữ 1 câu để tính pad
        pending = None
        for i, sentence in enumerate(sentences):
            audio = self.tts.generate(prepare_for_tts(sentence.text), speed=speed)
            raw = np.asarray(audio.samples, dtype=np.float32)
            if pending is None:
                pending = (_fade_edges(raw, sr), raw, sentence, i)
                continue
            p_faded, p_raw, p_sent, p_idx = pending
            pad = _pause_pad_samples(p_raw, raw, sr, gap_sec, target_sec)
            piece = np.concatenate([p_faded, np.zeros(pad, dtype=np.float32)])
            start_sec = cursor_samples / sr
            cursor_samples += len(piece)
            end_sec = (cursor_samples - pad) / sr
            yield make_timed(p_sent, start_sec, end_sec), piece, p_idx + 1, total
            pending = (_fade_edges(raw, sr), raw, sentence, i)

        if pending is not None:
            p_faded, _, p_sent, p_idx = pending
            start_sec = cursor_samples / sr
            cursor_samples += len(p_faded)
            end_sec = cursor_samples / sr
            yield make_timed(p_sent, start_sec, end_sec), p_faded, p_idx + 1, total
