from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

import numpy as np

# Chuyển HF cache về thư mục dự án (models/vieneu/hf_cache) TRƯỚC khi import vieneu.
# Khi frozen (PyInstaller): cache nằm cạnh EXE để ghi được, không ghi vào _MEIPASS.
from core.paths import app_dir as _app_dir

_BASE_DIR = _app_dir()
HF_CACHE_DIR = _BASE_DIR / "models" / "vieneu" / "hf_cache"
_HF_CACHE = HF_CACHE_DIR   # alias giữ tương thích code cũ
HF_CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("HF_HUB_CACHE", str(HF_CACHE_DIR))
# Nếu model đã có trong cache thì bỏ qua kiểm tra mạng (hoạt động offline 100%).
if any(HF_CACHE_DIR.glob("models--*")):
    os.environ.setdefault("HF_HUB_OFFLINE", "1")

SAMPLE_RATE = 48000

# Dấu hiệu lỗi "file không có trong cache" của huggingface_hub.
# Thông báo gốc tiếng Anh ("check your Internet connection") gây hiểu nhầm —
# thực tế nguyên nhân là "chưa tải model INT8" chứ không phải mất mạng.
_MISSING_CACHE_MARKERS = (
    "localentrynotfounderror",
    "offlinemodeisenabled",
    "local cache",
    "internet connection",
    "check your connection",
)


def _friendly_load_error(exc: Exception, precision: str) -> Exception:
    """Đổi lỗi kỹ thuật của SDK thành thông báo tiếng Việt dễ hiểu."""
    text = str(exc)
    hay = text.lower()
    if any(marker in hay for marker in _MISSING_CACHE_MARKERS) or \
            type(exc).__name__.lower() in _MISSING_CACHE_MARKERS:
        if precision == "int8":
            return RuntimeError(
                "Chưa tải model INT8 trên máy này. Mở ⚙ Cài đặt → bấm "
                "«Tải model INT8» (cần kết nối Internet một lần), hoặc "
                "chuyển lại FP32 trong Cài đặt."
            )
        return RuntimeError(
            "Không tìm thấy model trong cache. Hãy chạy lại "
            "download_model.py, hoặc kiểm tra kết nối Internet."
        )
    return exc


# Giọng tự thêm (clone) — nằm trong dự án, copy cả thư mục là mang theo.
CUSTOM_VOICES_PATH = _BASE_DIR / "models" / "vieneu" / "custom_voices.json"
# Định dạng file giọng di động (máy khỏe tạo -> copy sang máy yếu -> Nhập).
PORTABLE_FORMAT = "vieneu-turbo-voice"

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

# ── Giọng tùy chỉnh: file giọng di động (.json) + kho custom_voices.json ──


def _read_custom_store() -> dict:
    if not CUSTOM_VOICES_PATH.exists():
        return {}
    try:
        data = json.loads(CUSTOM_VOICES_PATH.read_text(encoding="utf-8"))
        voices = data.get("voices")
        return voices if isinstance(voices, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _write_custom_store(voices: dict) -> None:
    CUSTOM_VOICES_PATH.parent.mkdir(parents=True, exist_ok=True)
    CUSTOM_VOICES_PATH.write_text(
        json.dumps({"voices": voices}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _load_portable(path: str | Path) -> dict:
    p = Path(path)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError(f"Không đọc được file giọng: {exc}") from exc
    if not isinstance(data, dict) or data.get("format") != PORTABLE_FORMAT:
        raise ValueError("Không phải file giọng VieNeu đúng định dạng.")
    name = str(data.get("name") or "").strip()
    if not name:
        raise ValueError("File giọng thiếu tên.")
    if name in {vid for _, vid in PRESET_VOICES}:
        raise ValueError(f"Tên '{name}' trùng giọng preset có sẵn — hãy đổi tên file.")
    emb = data.get("speaker_emb")
    if not isinstance(emb, list) or not emb:
        raise ValueError("File giọng thiếu speaker_emb.")
    codes = data.get("codes")
    if codes is not None and not isinstance(codes, list):
        raise ValueError("File giọng codes không hợp lệ.")
    data["name"] = name
    return data


def _codes_to_array(codes) -> np.ndarray | None:
    """List JSON -> mảng (T, n_vq). File cũ lưu phẳng (T*n_vq,) -> reshape lại."""
    if not codes:
        return None
    arr = np.asarray(codes, dtype=np.int64)
    if arr.ndim == 1:
        if arr.size % 16 != 0:
            raise ValueError("File giọng codes không hợp lệ.")
        arr = arr.reshape(-1, 16)
    return arr


def _install_custom_voices(vieneu) -> None:
    """Nạp giọng tùy chỉnh từ custom_voices.json vào bảng preset của SDK."""
    from vieneu_utils.core_utils import strip_encoder_pad_frame
    for name, v in _read_custom_store().items():
        emb = v.get("speaker_emb")
        if not emb:
            continue
        try:
            codes = _codes_to_array(v.get("codes"))
        except ValueError:
            continue
        vieneu._preset_voices[name] = {
            "description": v.get("description", ""),
            "gender": v.get("gender", ""),
            "style": getattr(vieneu, "default_style", "tu_nhien"),
            "speaker_emb": np.asarray(emb, dtype=np.float32),
            "codes": strip_encoder_pad_frame(codes),
        }


class VieneuTTS:
    """Bọc SDK Vieneu v3 Turbo (48 kHz, ONNX CPU) với interface giống sherpa OfflineTTS.

    generate(text, speed) -> SimpleNamespace(samples, sample_rate)
    """

    def __init__(self, voice: str = "Hải Đăng", precision: str = "fp32",
                 threads: int = 0, device: str = "auto") -> None:
        """Bọc SDK VieNeu v3 Turbo (48 kHz).

        - precision: "fp32" (chất lượng cao, mặc định) | "int8" (nhanh ~1.6x,
          nhỏ ~4x, cần CPU có VNNI).
        - threads: số thread intra-op của ONNX Runtime (0 = tự động).
        - device: "auto" (tự dòng CUDA nếu đã cài PyTorch) | "cpu" | "cuda".
        """
        from vieneu import Vieneu

        try:
            self._vieneu = Vieneu(precision=precision, threads=threads, device=device)
        except Exception as exc:
            raise _friendly_load_error(exc, precision) from exc
        _install_custom_voices(self._vieneu)
        self._voice = voice
        self.sample_rate = SAMPLE_RATE

    def generate(self, text: str, speed: float = 1.0, **kwargs) -> SimpleNamespace:
        if not text.strip():
            return SimpleNamespace(samples=np.zeros(0, dtype=np.float32),
                                   sample_rate=self.sample_rate)
        # Lưu ý: SDK v3turbo KHÔNG có tham số `speed` (bị **kwargs bỏ qua) —
        # tốc độ chỉ được áp qua time-stretch (audio/speed.py) bên dưới.
        audio = self._vieneu.infer(text, voice=self._voice)
        samples = np.asarray(audio, dtype=np.float32).reshape(-1)
        samples = self._apply_speed(samples, speed)
        return SimpleNamespace(samples=samples, sample_rate=self.sample_rate)

    @staticmethod
    def _apply_speed(samples: np.ndarray, speed: float) -> np.ndarray:
        from audio.speed import apply_speed
        return apply_speed(samples, speed)

    # ── Giọng tùy chỉnh (không cần model: đọc/ghi JSON thuần) ──

    @staticmethod
    def list_custom_voice_names() -> list[str]:
        return list(_read_custom_store().keys())

    @staticmethod
    def read_portable_preview(path: str | Path) -> dict:
        """Đọc file giọng di động để hiện trước khi Nhập (không cần model)."""
        data = _load_portable(path)
        return {
            "name": data["name"],
            "description": str(data.get("description") or ""),
            "size": Path(path).stat().st_size,
        }

    @staticmethod
    def import_voice_file(path: str | Path) -> str:
        """Nhập file giọng di động vào custom_voices.json. Trả về tên giọng."""
        data = _load_portable(path)
        voices = _read_custom_store()
        voices[data["name"]] = {
            "description": str(data.get("description") or ""),
            "gender": str(data.get("gender") or ""),
            "speaker_emb": [float(x) for x in data["speaker_emb"]],
            "codes": data.get("codes"),  # list[int] hoặc list[list[int]] — giữ nguyên
        }
        _write_custom_store(voices)
        return data["name"]

    @staticmethod
    def delete_custom_voice(name: str) -> None:
        voices = _read_custom_store()
        if name in voices:
            del voices[name]
            _write_custom_store(voices)

    @staticmethod
    def export_voice_file(name: str, out_path: str | Path) -> str:
        """Xuất 1 giọng tùy chỉnh ra file di động (mang sang máy khác)."""
        voices = _read_custom_store()
        if name not in voices:
            raise ValueError(f"Chưa có giọng tùy chỉnh tên '{name}'.")
        v = voices[name]
        data = {
            "format": PORTABLE_FORMAT,
            "version": 1,
            "name": name,
            "description": v.get("description", ""),
            "gender": v.get("gender", ""),
            "speaker_emb": v.get("speaker_emb") or [],
            "codes": v.get("codes") or [],
        }
        out = Path(out_path)
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        return str(out)

    def create_voice_from_sample(self, name: str, ref_audio: str | Path,
                                 description: str = "",
                                 denoise: bool = True) -> None:
        """Tạo giọng từ file mẫu (cần nạp model — chạy ở máy khỏe / CLI)."""
        name = name.strip()
        if not name:
            raise ValueError("Tên giọng không được để trống.")
        if name in {vid for _, vid in PRESET_VOICES}:
            raise ValueError(f"Tên '{name}' trùng giọng preset có sẵn.")
        if name in _read_custom_store():
            raise ValueError(f"Đã có giọng tùy chỉnh tên '{name}'.")
        self._vieneu.add_voice(name, ref_audio, denoise=denoise,
                               description=description)
        entry = self._vieneu._preset_voices[name]
        codes = entry.get("codes")
        voices = _read_custom_store()
        voices[name] = {
            "description": description,
            "gender": str(entry.get("gender") or ""),
            "speaker_emb": [round(float(x), 6) for x in
                            np.asarray(entry["speaker_emb"]).reshape(-1)],
            "codes": None if codes is None else
                     np.asarray(codes, dtype=np.int64).tolist(),  # giữ shape (T, n_vq)
        }
        _write_custom_store(voices)
