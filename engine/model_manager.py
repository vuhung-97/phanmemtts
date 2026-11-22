from __future__ import annotations

import gc
import json
from pathlib import Path

from core.app_info import total_ram_gb
from core.models import VoiceModelInfo
from core.paths import app_dir

BASE_DIR = app_dir()
MODELS_DIR = BASE_DIR / "models"

# Ngưỡng RAM để bật chế độ tiết kiệm ONNX khi setting = "auto".
# Máy 8-16 GB vẫn có thể thấy RAM tăng ~2,4 GB khi tổng hợp, nên ưu tiên
# tiết kiệm; máy > 16 GB giữ tốc độ.
LOW_MEMORY_RAM_GB = 16.0

# Thư mục model không dùng nữa (đã gỡ ở v1.8.0) — giữ để dọn dẹp cache.
_LEGACY_MODEL_DIRS = ("kokoro_vi",)


class ModelManager:
    """Quét thư mục models/ và quản lý vòng đời model (lazy-load, tiết kiệm RAM).

    Cấu hình runtime (precision / threads) lấy từ Cài đặt:
    - precision: "fp32" (mặc định) | "int8" (nhanh hơn, cần CPU có VNNI)
    - threads: số thread ONNX Runtime (0 = tự động)

    Bản phát hành chỉ chạy CPU (không kèm PyTorch/GPU).
    """

    def __init__(self, models_dir: Path = MODELS_DIR, precision: str = "fp32",
                 threads: int = 0, onnx_memory: str = "auto") -> None:
        self.models_dir = models_dir
        self.precision = precision
        self.threads = int(threads)
        self.onnx_memory = onnx_memory
        self._loaded_id: str | None = None
        self._loaded_tts = None
        # (engine, precision, threads, low_memory) của instance đang nạp.
        self._loaded_key: tuple | None = None

    # ── Cấu hình runtime ──

    def low_memory(self) -> bool:
        """Chế độ tiết kiệm RAM ONNX: "auto" theo dung lượng máy."""
        if self.onnx_memory == "on":
            return True
        if self.onnx_memory == "off":
            return False
        ram = total_ram_gb()
        return bool(ram and ram <= LOW_MEMORY_RAM_GB)

    def _runtime_key(self, engine: str) -> tuple:
        return (engine, self.precision, self.threads, self.low_memory())

    def set_runtime(self, precision: str | None = None,
                    threads: int | None = None,
                    onnx_memory: str | None = None) -> None:
        """Đổi cấu hình runtime. Nếu model đang nạp khác cấu hình → nạp lại."""
        changed = (
            (precision is not None and precision != self.precision)
            or (threads is not None and int(threads) != self.threads)
        )
        if onnx_memory is not None and onnx_memory != self.onnx_memory:
            changed = True
        if precision is not None:
            self.precision = precision
        if threads is not None:
            self.threads = int(threads)
        if onnx_memory is not None:
            self.onnx_memory = onnx_memory
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
                    display_name=label,
                    language="vi",
                    model_path=marker,
                    config_path=marker,
                    tokens_path=marker,
                    data_dir=self.models_dir / "vieneu",
                    engine="vieneu",
                )
            )
        # Giọng tùy chỉnh (import file từ máy khác / tạo bằng CLI)
        # Không gắn hậu tố vào tên hiển thị: combo giọng chỉ rộng 180px, hậu tố
        # làm tên bị cắt. Giọng tùy chỉnh đã được phân biệt trong dialog quản lý
        # giọng (có nút xuất ⬇ / xoá 🗑 riêng).
        for custom in VieneuTTS.list_custom_voice_names():
            results.append(
                VoiceModelInfo(
                    model_id=f"vieneu:{custom}",
                    display_name=custom,
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
        """Nạp model vào RAM; đổi giọng cùng engine chỉ gọi ``set_voice``.

        Quan trọng: mỗi giọng preset là một ``model_id`` khác nhau nhưng dùng
        chung một model. Nạp lại cả model mỗi lần đổi giọng tốn 13-20 giây và
        vài trăm MB native không trả về OS -> RAM tăng dần khi người dùng đổi
        giọng. Vì vậy cache theo (engine, precision, threads, low_memory).
        """
        key = self._runtime_key(info.engine)
        if self._loaded_tts is not None and self._loaded_key == key:
            if self._loaded_id != info.model_id:
                set_voice = getattr(self._loaded_tts, "set_voice", None)
                if callable(set_voice):
                    set_voice(info.model_id)
            self._loaded_id = info.model_id
            return self._loaded_tts
        self.unload()
        self._loaded_tts = _build_tts(info, self.precision, self.threads,
                                      self.low_memory())
        self._loaded_key = key
        self._loaded_id = info.model_id
        gc.collect()
        return self._loaded_tts

    def unload(self) -> None:
        if self._loaded_tts is not None:
            close = getattr(self._loaded_tts, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass
            self._loaded_tts = None
            self._loaded_id = None
            self._loaded_key = None
            gc.collect()

    def unload_if(self, model_id: str) -> None:
        """Giải phóng nếu đúng model này đang nạp (vd: giọng bị ghi đè/xóa)."""
        if self._loaded_id == model_id:
            self.unload()

    def refresh_custom_voices(self) -> None:
        """Cập nhật giọng tùy chỉnh trong model đang nạp (không nạp lại model)."""
        refresh = getattr(self._loaded_tts, "refresh_custom_voices", None)
        if callable(refresh):
            refresh()


def _build_tts(info: VoiceModelInfo, precision: str, threads: int,
               low_memory: bool = False):
    if info.engine == "vieneu":
        from engine.vieneu_engine import VieneuTTS

        voice_id = info.model_id.split(":", 1)[-1] if ":" in info.model_id else "Hải Đăng"
        return VieneuTTS(voice=voice_id, precision=precision, threads=threads,
                         low_memory=low_memory)

    raise ValueError(f"Unknown engine: {info.engine}")
