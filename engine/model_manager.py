from __future__ import annotations

import gc
import json
from pathlib import Path

from core.models import VoiceModelInfo

BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"
SHARED_DIR = MODELS_DIR / "shared"

_DISPLAY_NAMES = {
    "en": "Tiếng Anh",
}


class ModelManager:
    """Quét thư mục models/ và quản lý vòng đời model (lazy-load, tiết kiệm RAM)."""

    def __init__(self, models_dir: Path = MODELS_DIR) -> None:
        self.models_dir = models_dir
        self._loaded_id: str | None = None
        self._loaded_tts = None

    def scan(self) -> list[VoiceModelInfo]:
        results: list[VoiceModelInfo] = []
        if not self.models_dir.exists():
            return results
        for folder in sorted(self.models_dir.iterdir()):
            if not folder.is_dir() or folder.name in ("shared", "kokoro_vi"):
                continue
            if folder.name == "vieneu":
                results.extend(self._scan_vieneu())
                continue
            onnx_files = sorted(
                p for p in folder.glob("*.onnx") if p.is_file()
            )
            if not onnx_files:
                continue
            model_path = onnx_files[0]
            tokens_path = folder / "tokens.txt"
            if not tokens_path.exists():
                tokens_path = self.models_dir / "shared" / "tokens.txt"
            if not tokens_path.exists():
                continue
            data_dir = self._resolve_data_dir(folder)
            config_path = folder / f"{model_path.name}.json"
            results.append(
                VoiceModelInfo(
                    model_id=folder.name,
                    display_name=self._display_name(folder),
                    language=self._language(folder),
                    model_path=model_path,
                    config_path=config_path,
                    tokens_path=tokens_path,
                    data_dir=data_dir,
                )
            )
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

    def _resolve_data_dir(self, folder: Path) -> Path:
        own = folder / "espeak-ng-data"
        if own.exists():
            return own
        shared = self.models_dir / "shared" / "espeak-ng-data"
        if shared.exists():
            return shared
        for sibling in sorted(self.models_dir.iterdir()):
            candidate = sibling / "espeak-ng-data"
            if sibling.is_dir() and candidate.exists():
                return candidate
        return own

    @staticmethod
    def _display_name(folder: Path) -> str:
        meta = folder / "voice.json"
        if meta.exists():
            try:
                data = json.loads(meta.read_text(encoding="utf-8"))
                if data.get("display_name"):
                    return str(data["display_name"])
            except (json.JSONDecodeError, OSError):
                pass
        prefix = folder.name.split("_")[0]
        return _DISPLAY_NAMES.get(prefix, folder.name)

    @staticmethod
    def _language(folder: Path) -> str:
        meta = folder / "voice.json"
        if meta.exists():
            try:
                data = json.loads(meta.read_text(encoding="utf-8"))
                if data.get("language"):
                    return str(data["language"])
            except (json.JSONDecodeError, OSError):
                pass
        return folder.name.split("_")[0]

    def get(self, model_id: str) -> VoiceModelInfo | None:
        for info in self.scan():
            if info.model_id == model_id:
                return info
        return None

    def load_tts(self, info: VoiceModelInfo, num_threads: int = 2):
        """Nạp model vào RAM; nếu đã nạp model khác thì giải phóng trước."""
        if self._loaded_id == info.model_id and self._loaded_tts is not None:
            return self._loaded_tts
        self.unload()
        self._loaded_tts = _build_tts(info, num_threads)
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


def _build_tts(info: VoiceModelInfo, num_threads: int):
    if info.engine == "vieneu":
        from engine.vieneu_engine import VieneuTTS

        voice_id = info.model_id.split(":", 1)[-1] if ":" in info.model_id else "Hải Đăng"
        return VieneuTTS(voice=voice_id, num_threads=num_threads)

    raise ValueError(f"Unknown engine: {info.engine}")
