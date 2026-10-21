from __future__ import annotations

import gc
import json
from pathlib import Path

from core.models import VoiceModelInfo
from core.paths import app_dir

BASE_DIR = app_dir()
MODELS_DIR = BASE_DIR / "models"

# Thư mục model không dùng nữa (đã gỡ ở v1.8.0) — giữ để dọn dẹp cache.
_LEGACY_MODEL_DIRS = ("kokoro_vi",)


class ModelManager:
    """Quét thư mục models/ và quản lý vòng đời model (lazy-load, tiết kiệm RAM).

    Cấu hình runtime (precision / threads / device) lấy từ Cài đặt:
    - precision: "fp32" (mặc định) | "int8" (nhanh hơn, cần CPU có VNNI)
    - threads: số thread ONNX Runtime (0 = tự động)
    - device: "auto" | "cpu" | "cuda"
    """

    def __init__(self, models_dir: Path = MODELS_DIR, precision: str = "fp32",
                 threads: int = 0, device: str = "auto") -> None:
        self.models_dir = models_dir
        self.precision = precision
        self.threads = int(threads)
        self.device = device
        self._loaded_id: str | None = None
        self._loaded_tts = None

    # ── Cấu hình runtime ──

    def set_runtime(self, precision: str | None = None, threads: int | None = None,
                    device: str | None = None) -> None:
        """Đổi cấu hình runtime. Nếu model đang nạp khác cấu hình → nạp lại."""
        changed = (
            (precision is not None and precision != self.precision)
            or (threads is not None and int(threads) != self.threads)
            or (device is not None and device != self.device)
        )
        if precision is not None:
            self.precision = precision
        if threads is not None:
            self.threads = int(threads)
        if device is not None:
            self.device = device
        if changed:
            self.unload()

    # ── Quét model ──

    def scan(self) -> list[VoiceModelInfo]:
        results: list[VoiceModelInfo] = []
        if not self.models_dir.exists():
            return results
        for folder in sorted(self.models_dir.iterdir()):
            if not folder.is_dir() or folder.name in ("shared", *_LEGACY_MODEL_DIRS):
                continue
            if folder.name == "vieneu":
                results.extend(self._scan_vieneu())
        return results

    def _scan_vieneu(self) -> list[VoiceModelInfo]:
        """Mỗi giọng preset VieNeu là một entry riêng (engine vieneu)."""
        from engine.vieneu_engine import PRESET_VOICES, VieneuTTS

        marker = self.models_dir / "vieneu" / "voice.json"
        if not marker.exists():
            return []
        results: list[VoiceModelInfo] = []
        for label, voice_id in PRESET_VOICES:
            results.append(
                VoiceModelInfo(
                    model_id=f"vieneu:{voice_id}",
                    display_name=f"{label} (VieNeu)",
                    language="vi",
                    model_path=marker,
                    config_path=marker,
                    tokens_path=marker,
                    data_dir=self.models_dir / "vieneu",
                    engine="vieneu",
                )
            )
        # Giọng tùy chỉnh (import file từ máy khác / tạo bằng CLI)
        for custom in VieneuTTS.list_custom_voice_names():
            results.append(
                VoiceModelInfo(
                    model_id=f"vieneu:{custom}",
                    display_name=f"{custom} (Tùy chỉnh)",
                    language="vi",
                    model_path=marker,
                    config_path=marker,
                    tokens_path=marker,
                    data_dir=self.models_dir / "vieneu",
                    engine="vieneu",
                )
            )
        return results

    def get(self, model_id: str) -> VoiceModelInfo | None:
        for info in self.scan():
            if info.model_id == model_id:
                return info
        return None

    # ── Nạp / giải phóng ──

    def load_tts(self, info: VoiceModelInfo):
        """Nạp model vào RAM; nếu đã nạp model khác thì giải phóng trước."""
        if self._loaded_id == info.model_id and self._loaded_tts is not None:
            return self._loaded_tts
        self.unload()
        self._loaded_tts = _build_tts(info, self.precision, self.threads, self.device)
        self._loaded_id = info.model_id
        gc.collect()
        return self._loaded_tts

    def unload(self) -> None:
        if self._loaded_tts is not None:
            self._loaded_tts = None
            self._loaded_id = None
            gc.collect()

    def unload_if(self, model_id: str) -> None:
        """Giải phóng nếu đúng model này đang nạp (vd: giọng bị ghi đè/xóa)."""
        if self._loaded_id == model_id:
            self.unload()


def _build_tts(info: VoiceModelInfo, precision: str, threads: int, device: str):
    if info.engine == "vieneu":
        from engine.vieneu_engine import VieneuTTS

        voice_id = info.model_id.split(":", 1)[-1] if ":" in info.model_id else "Hải Đăng"
        return VieneuTTS(voice=voice_id, precision=precision, threads=threads,
                         device=device)

    raise ValueError(f"Unknown engine: {info.engine}")
