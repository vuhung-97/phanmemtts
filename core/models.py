from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class VoiceModelInfo:
    model_id: str
    display_name: str
    language: str
    model_path: Path
    config_path: Path
    tokens_path: Path
    data_dir: Path
    engine: str = "vieneu"
    voicepack_path: Path | None = None


@dataclass(frozen=True)
class SentenceItem:
    index: int
    text: str
    char_start: int
    char_end: int
    start_sec: float = 0.0
    end_sec: float = 0.0


@dataclass
class TimelineMap:
    sentences: list[SentenceItem] = field(default_factory=list)
    sample_rate: int = 22050

    @property
    def total_duration(self) -> float:
        if not self.sentences:
            return 0.0
        return self.sentences[-1].end_sec

    def find_index_by_time(self, seconds: float) -> int:
        if not self.sentences:
            return -1
        if seconds < 0:
            return 0
        for i, item in enumerate(self.sentences):
            if item.start_sec <= seconds < item.end_sec:
                return item.index
            next_start = (
                self.sentences[i + 1].start_sec
                if i + 1 < len(self.sentences)
                else float("inf")
            )
            if item.end_sec <= seconds < next_start:
                return item.index
        if seconds >= self.sentences[-1].end_sec:
            return self.sentences[-1].index
        return 0


@dataclass
class TrackSegment:
    path: str
    start_sec: float = 0.0
    end_sec: float | None = None   # None = đến hết file


@dataclass
class MusicMergeConfig:
    voice_path: str
    intro: TrackSegment | None = None
    bg: TrackSegment | None = None
    outro: TrackSegment | None = None
    intro_volume: float = 0.7
    bg_volume: float = 0.15
    outro_volume: float = 0.7
    crossfade_sec: float = 0.5
