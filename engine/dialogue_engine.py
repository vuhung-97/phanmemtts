"""Dựng audio hội thoại nhiều giọng từ ``DialogueScript``.

Mỗi lượt dùng đúng giọng của nhân vật (``tts.set_voice`` — không nạp lại
model), chèn khoảng lặng giữa các lượt, ghép timeline quy về ký tự của
**kịch bản gốc** để highlight đúng chỗ trong editor.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

import numpy as np

from audio.buffer import GrowableBuffer
from audio.speed import apply_speed
from core.dialogue import DialogueScript
from core.models import SentenceItem, TimelineMap
from core.text_processor import build_sentences
from engine.tts_engine import TtsEngine


class DialogueCancelled(Exception):
    """Người dùng bấm Dừng giữa chừng."""


@dataclass
class RenderedDialogue:
    source: object
    sample_rate: int
    timeline: TimelineMap


def _resolve_voice(speaker: str,
                   voices: Mapping[str, str] | Callable[[str], str | None]
                   ) -> str:
    voice = voices(speaker) if callable(voices) else voices.get(speaker)
    if not voice:
        raise ValueError(f"Chưa gán giọng cho nhân vật '{speaker}'.")
    return voice


def render_dialogue(
    script: DialogueScript,
    tts,
    voices: Mapping[str, str] | Callable[[str], str | None],
    *,
    gap_sec: float = 0.5,
    speed: float = 1.0,
    store=None,
    progress: Callable[[int, int, int, int], None] | None = None,
    cancel=None,
) -> RenderedDialogue:
    """Trả ``RenderedDialogue`` (source + sample_rate + timeline).

    - ``voices``: mapping ``{tên nhân vật: model_id}`` hoặc hàm nhận tên.
    - ``store``: source có ``append``/``total_samples`` — mặc định
      ``GrowableBuffer``; page có thể truyền ``TempSession`` để ghi ra đĩa.
    - ``progress(turn_index, turn_total, sentence_index, sentence_total)``.
    - ``cancel``: ``threading.Event``; dừng giữa chừng → ``DialogueCancelled``.
    """
    if not script.turns:
        raise ValueError("Kịch bản không có lượt nói nào.")

    engine = TtsEngine(tts)
    sr = engine.sample_rate
    buffer = store if store is not None else GrowableBuffer()
    speed = max(float(speed or 1.0), 0.1)

    total_sentences = sum(len(build_sentences(turn.text))
                          for turn in script.turns)

    sentences: list[SentenceItem] = []
    cursor = 0
    global_index = 0
    turn_total = len(script.turns)
    gap_samples = max(0, int(round(gap_sec / speed * sr)))

    for turn_index, turn in enumerate(script.turns, start=1):
        voice = _resolve_voice(turn.speaker, voices)
        tts.set_voice(voice.split(":", 1)[-1] if voice.startswith("vieneu:")
                      else voice)
        produced = False
        for timed, piece, _cur, _tot in engine.synthesize_stream(turn.text,
                                                                 speed=1.0):
            if cancel is not None and cancel.is_set():
                raise DialogueCancelled()
            if piece.size:
                out = (apply_speed(piece, speed)
                       if abs(speed - 1.0) > 1e-9 else piece)
                start_sec = cursor / sr
                duration = (timed.end_sec - timed.start_sec) / speed
                sentences.append(SentenceItem(
                    index=global_index,
                    text=timed.text,
                    char_start=turn.char_start + timed.char_start,
                    char_end=turn.char_start + timed.char_end,
                    start_sec=start_sec,
                    end_sec=start_sec + max(duration, 0.0),
                ))
                global_index += 1
                buffer.append(out)
                cursor += len(out)
                produced = True
            if progress is not None:
                progress(turn_index, turn_total, global_index,
                         max(total_sentences, global_index))
        if produced and turn_index < turn_total and gap_samples > 0:
            buffer.append(np.zeros(gap_samples, dtype=np.float32))
            cursor += gap_samples

    timeline = TimelineMap(sentences=sentences, sample_rate=sr)
    return RenderedDialogue(source=buffer, sample_rate=sr, timeline=timeline)
