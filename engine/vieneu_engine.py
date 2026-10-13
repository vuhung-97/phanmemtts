from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import numpy as np

# Chuyển HF cache về thư mục dự án (models/vieneu/hf_cache) TRƯỚC khi import vieneu.
_BASE_DIR = Path(__file__).resolve().parent.parent
_HF_CACHE = _BASE_DIR / "models" / "vieneu" / "hf_cache"
_HF_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("HF_HUB_CACHE", str(_HF_CACHE))
# Nếu model đã có trong cache thì bỏ qua kiểm tra mạng (hoạt động offline 100%).
if any(_HF_CACHE.glob("models--*")):
    os.environ.setdefault("HF_HUB_OFFLINE", "1")

SAMPLE_RATE = 48000

# 25 giọng preset VieNeu v3 Turbo — khớp thứ tự và tên trong
# vieneu/assets/voices_v3_turbo.json (hardcode để scan() không cần load model ~19s).
PRESET_VOICES: list[tuple[str, str]] = [
    ("Adam bựa (Nam, Bắc)", "Adam bựa"),
    ("Trúc Ly (Nữ, Bắc)", "Trúc Ly"),
    ("Thiện Minh (Nam, Bắc)", "Thiện Minh"),
    ("Mai Anh (Nữ, Bắc)", "Mai Anh"),
    ("Hải Đăng (Nam, Bắc)", "Hải Đăng"),
    ("Thùy Dung (Nữ, Nam)", "Thùy Dung"),
    ("Thiền Tâm Đức (Nam, Bắc)", "Thiền Tâm Đức"),
    ("Ngọc Huyền (Nữ, Bắc)", "Ngọc Huyền"),
    ("Quang Sơn (Nam, Trung)", "Quang Sơn"),
    ("Ngọc Trân (Nữ, Trung)", "Ngọc Trân"),
    ("Minh Đức (Nam, Bắc)", "Minh Đức"),
    ("Phạm Tuyên (Nam, Bắc)", "Phạm Tuyên"),
    ("Thái Sơn (Nam, Nam)", "Thái Sơn"),
    ("Xuân Vĩnh (Nam, Bắc)", "Xuân Vĩnh"),
    ("Thanh Bình (Nam, Bắc)", "Thanh Bình"),
    ("Ngọc Linh (Nữ, Bắc)", "Ngọc Linh"),
    ("Đoan Trang (Nữ, Bắc)", "Đoan Trang"),
    ("Thục Đoan (Nữ, Nam)", "Thục Đoan"),
    ("Minh Triết (Nam, Nam)", "Minh Triết"),
    ("Mỹ Duyên (Nữ, Nam)", "Mỹ Duyên"),
    ("Quỳnh Anh (Nữ, Bắc)", "Quỳnh Anh"),
    ("Đức Trí (Nam, Nam)", "Đức Trí"),
    ("Kim Thanh (Nữ, Nam)", "Kim Thanh"),
    ("Adam (Nam, Nam)", "Adam"),
    ("Quốc Tuấn (Nam, Bắc)", "Quốc Tuấn"),
]


class VieneuTTS:
    """Bọc SDK Vieneu v3 Turbo (48 kHz, ONNX CPU) với interface giống sherpa OfflineTTS.

    generate(text, speed) -> SimpleNamespace(samples, sample_rate)
    """

    def __init__(self, voice: str = "Hải Đăng", precision: str = "fp32",
                 num_threads: int = 2) -> None:
        from vieneu import Vieneu

        self._vieneu = Vieneu(precision=precision)
        self._voice = voice
        self.sample_rate = SAMPLE_RATE

    def generate(self, text: str, speed: float = 1.0, **kwargs) -> SimpleNamespace:
        if not text.strip():
            return SimpleNamespace(samples=np.zeros(0, dtype=np.float32),
                                   sample_rate=self.sample_rate)
        audio = self._vieneu.infer(text, voice=self._voice, speed=speed)
        samples = np.asarray(audio, dtype=np.float32).reshape(-1)
        samples = self._apply_speed(samples, speed)
        return SimpleNamespace(samples=samples, sample_rate=self.sample_rate)

    @staticmethod
    def _apply_speed(samples: np.ndarray, speed: float) -> np.ndarray:
        """Speed thật: model không hỗ trợ -> time-stretch sau khi sinh (giữ cao độ)."""
        if abs(speed - 1.0) < 0.01 or len(samples) < 1024:
            return samples
        try:
            from librosa import effects
            out = effects.time_stretch(samples, rate=float(speed))
            return np.asarray(out, dtype=np.float32)
        except Exception:
            return samples   # fail-safe: giữ audio gốc, không crash export
