"""Kiểm thử kịch bản hội thoại + engine nhiều giọng."""

from __future__ import annotations

import threading
from types import SimpleNamespace

import numpy as np
import pytest

from core import dialogue
from core.text_processor import clean_for_reading
from engine.dialogue_engine import (DialogueCancelled, render_dialogue)
from engine.tts_engine import TtsEngine

SR = 48000


# ── Parse ──

def test_parse_two_speakers():
    script = dialogue.parse_script("An: Xin chào.\nBình: Chào An.")
    assert [t.speaker for t in script.turns] == ["An", "Bình"]
    assert script.speakers == ["An", "Bình"]
    assert script.ok


def test_missing_name_is_error():
    script = dialogue.parse_script("An: Xin chào.\nDòng không tên.")
    assert not script.ok
    assert any(issue.line_no == 2 and "thiếu 'Tên:'" in issue.message
               for issue in script.issues)


def test_empty_content_is_error():
    script = dialogue.parse_script("An:")
    assert not script.ok
    assert any("thiếu nội dung" in i.message for i in script.issues)


def test_empty_name_is_error():
    script = dialogue.parse_script(": nội dung")
    assert not script.ok


def test_colon_inside_content():
    script = dialogue.parse_script("An: Giờ họp là 8:30 sáng.")
    assert script.turns[0].text == "Giờ họp là 8:30 sáng."


def test_comment_and_blank_lines_skipped():
    script = dialogue.parse_script("# chú thích\n\nAn: A.\n\nBình: B.")
    assert len(script.turns) == 2


def test_duplicate_name_casefold_merges():
    script = dialogue.parse_script("An: Một.\nan: Hai.")
    assert [t.speaker for t in script.turns] == ["An", "An"]
    assert script.speakers == ["An"]
    assert script.warnings


def test_long_or_bracket_name_is_error():
    assert not dialogue.parse_script("A" * 41 + ": x").ok
    assert not dialogue.parse_script("An[1]: x").ok


def test_char_offsets_point_to_content():
    text = "# ghi chú\nAn: Xin chào.\nBình: Chào."
    script = dialogue.parse_script(text)
    first, second = script.turns
    assert text[first.char_start:first.char_end] == "Xin chào."
    assert text[second.char_start:second.char_end] == "Chào."


def test_empty_script():
    script = dialogue.parse_script("   \n\n")
    assert not script.ok
    assert "trống" in script.issues[0].message.lower()


def test_turns_of():
    script = dialogue.parse_script("An: A.\nBình: B.\nAn: C.")
    assert script.turns_of("An") == 2
    assert script.turns_of("Bình") == 1


def test_only_comments_has_no_turns():
    script = dialogue.parse_script("# chỉ chú thích")
    assert not script.ok


# ── Cast / draft ──

def test_cast_roundtrip(monkeypatch, tmp_path):
    path = tmp_path / "cast.json"
    monkeypatch.setattr(dialogue, "cast_path", lambda: path)
    dialogue.save_cast({"An": "vieneu:Adam bựa", "Bình": ""})
    assert dialogue.load_cast() == {"An": "vieneu:Adam bựa"}


def test_cast_corrupt_returns_empty(monkeypatch, tmp_path):
    path = tmp_path / "cast.json"
    path.write_text("{ hỏng", encoding="utf-8")
    monkeypatch.setattr(dialogue, "cast_path", lambda: path)
    assert dialogue.load_cast() == {}


def test_draft_roundtrip(monkeypatch, tmp_path):
    path = tmp_path / "draft.txt"
    monkeypatch.setattr(dialogue, "draft_path", lambda: path)
    dialogue.save_draft("An: Xin chào.")
    assert dialogue.load_draft() == "An: Xin chào."


def test_clean_keeps_speaker_lines():
    text = "An: một câu khá dài\nBình: câu tiếp theo"
    cleaned, changes = clean_for_reading(text)
    assert cleaned == text
    assert changes == 0


# ── Engine ──

class FakeTTS:
    sample_rate = SR

    def __init__(self, dur: float = 0.2) -> None:
        self.dur = dur
        self.voices: list[str] = []
        self.calls: list[str] = []

    def set_voice(self, voice: str) -> None:
        self.voices.append(voice)

    def generate(self, text: str, speed: float = 1.0, **kwargs):
        self.calls.append(text)
        n = int(self.dur * SR)
        return SimpleNamespace(samples=np.full(n, 0.1, dtype=np.float32),
                               sample_rate=SR)


def test_render_switches_voice_per_turn():
    script = dialogue.parse_script("An: Một câu.\nBình: Hai câu.")
    tts = FakeTTS()
    render_dialogue(script, tts, {"An": "vieneu:Adam bựa",
                                  "Bình": "vieneu:Trúc Ly"}, gap_sec=0.0)
    assert tts.voices == ["Adam bựa", "Trúc Ly"]


def test_render_timeline_maps_to_script_offsets():
    text = "An: Một câu.\nBình: Hai câu."
    script = dialogue.parse_script(text)
    result = render_dialogue(script, FakeTTS(), {"An": "A", "Bình": "B"},
                             gap_sec=0.0)
    assert len(result.timeline.sentences) == 2
    first, second = result.timeline.sentences
    assert (first.char_start, first.char_end) == (
        script.turns[0].char_start,
        script.turns[0].char_end)
    assert text[first.char_start:first.char_end] == "Một câu."
    assert text[second.char_start:second.char_end] == "Hai câu."
    assert [s.index for s in result.timeline.sentences] == [0, 1]


def test_render_inserts_gap_between_turns():
    script = dialogue.parse_script("An: A.\nBình: B.")
    no_gap = render_dialogue(script, FakeTTS(), {"An": "A", "Bình": "B"},
                             gap_sec=0.0)
    with_gap = render_dialogue(script, FakeTTS(), {"An": "A", "Bình": "B"},
                               gap_sec=0.5)
    no_gap_samples = int(no_gap.source.total_samples)
    gap_samples = int(with_gap.source.total_samples)
    assert gap_samples - no_gap_samples == pytest.approx(0.5 * SR, abs=SR * 0.03)


def test_render_speed_scales_duration():
    script = dialogue.parse_script("An: A.\nBình: B.")
    normal = render_dialogue(script, FakeTTS(), {"An": "A", "Bình": "B"},
                             gap_sec=0.5, speed=1.0)
    faster = render_dialogue(script, FakeTTS(), {"An": "A", "Bình": "B"},
                             gap_sec=0.5, speed=2.0)
    ratio = faster.source.total_samples / normal.source.total_samples
    assert ratio == pytest.approx(0.5, abs=0.06)


def test_render_missing_voice_raises():
    script = dialogue.parse_script("An: A.")
    with pytest.raises(ValueError, match="Chưa gán giọng"):
        render_dialogue(script, FakeTTS(), {})


def test_render_cancel():
    script = dialogue.parse_script("An: A.\nBình: B.")
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(DialogueCancelled):
        render_dialogue(script, FakeTTS(), {"An": "A", "Bình": "B"},
                        cancel=cancel)


def test_render_progress_called():
    calls: list[tuple] = []
    script = dialogue.parse_script("An: A.\nBình: B.")
    render_dialogue(script, FakeTTS(), {"An": "A", "Bình": "B"},
                    progress=lambda *args: calls.append(args))
    assert calls
    assert calls[-1][0] == 2


def test_tts_engine_sentence_offsets_relative_turn():
    engine = TtsEngine(FakeTTS())
    out = list(engine.synthesize_stream("Một. Hai."))
    assert len(out) == 2
    assert out[0][0].char_start == 0
