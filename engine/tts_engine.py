from __future__ import annotations

from typing import Iterator

import numpy as np

from core.models import SentenceItem, TimelineMap
from core.text_normalizer import normalize_numbers_vi
from core.text_processor import build_sentences

GAP_SEC = 0.25
SILENCE_SAMPLE_RATE = 22050
_TERMINAL_CHARS = ".?!…"
_SPECIAL_QUOTES = {
    "“": '"', "”": '"', "„": '"', "‟": '"',
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
    "–": "-", "—": "-", "…": "...",
}


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
        """Generator trả về từng câu ngay khi tổng hợp xong:

        yields: (SentenceItem, piece_waveform, current_idx_1based, total_sentences)
        """
        sentences = build_sentences(text)
        if not sentences:
            return

        gap = int((GAP_SEC / max(speed, 0.1)) * self.sample_rate)
        cursor_samples = 0
        total = len(sentences)

        for i, sentence in enumerate(sentences):
            audio = self.tts.generate(prepare_for_tts(sentence.text), speed=speed)
            samples = np.asarray(audio.samples, dtype=np.float32)
            piece = np.concatenate([samples, np.zeros(gap, dtype=np.float32)])

            start_sec = cursor_samples / self.sample_rate
            cursor_samples += len(piece)
            end_sec = (cursor_samples - gap) / self.sample_rate

            timed = SentenceItem(
                index=sentence.index,
                text=sentence.text,
                char_start=sentence.char_start,
                char_end=sentence.char_end,
                start_sec=start_sec,
                end_sec=max(end_sec, start_sec),
            )
            yield timed, piece, i + 1, total
