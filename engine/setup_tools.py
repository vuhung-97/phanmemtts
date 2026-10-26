"""Kiểm tra bộ cài (model kèm sẵn) và năng lực CPU.

Bản phát hành chép sẵn toàn bộ model vào ``models/vieneu/`` nên app KHÔNG tải
gì từ mạng. Module này chỉ đọc trạng thái file trên đĩa — không gọi mạng,
không ``pip install``.
"""

from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path

MODEL_REPO = "pnnbao-ump/VieNeu-TTS-v3-Turbo"

# File model FP32 (thư mục onnx_update, ~453 MB).
FP32_FILES = (
    "config.json",
    "tokenizer.json",
    "vieneu_acoustic_cached.onnx",
    "vieneu_backbone_shared.data",
    "vieneu_decode_step.onnx",
    "vieneu_prefill.onnx",
    "vieneu_v3_heads.npz",
)

# File model INT8 (thư mục onnx_int8, ~158 MB) — kèm sẵn trong bản phát hành.
INT8_FILES = FP32_FILES

# File nằm ở gốc repo model (dùng cho tạo giọng mới).
ROOT_FILES = (
    "config.json",
    "speaker_encoder.onnx",
    "denoiser.onnx",
)


# ── Đường dẫn cache ──────────────────────────────────────────────────────────

def _cache_dir() -> Path:
    from engine.vieneu_engine import HF_CACHE_DIR

    return HF_CACHE_DIR


def _snapshot_root() -> Path:
    return (_cache_dir()
            / f"models--{MODEL_REPO.replace('/', '--')}" / "snapshots")


def _snapshot_dir() -> Path | None:
    """Thư mục snapshot có model FP32 trong cache (None nếu chưa có)."""
    root = _snapshot_root()
    if not root.is_dir():
        return None
    for folder in sorted(root.iterdir()):
        if (folder / "onnx_update").is_dir():
            return folder
    return None


# ── Model INT8 ────────────────────────────────────────────────────────────────

def int8_dir() -> Path | None:
    """Thư mục chứa đủ bộ file INT8 trong bản cài (None nếu thiếu)."""
    root = _snapshot_root()
    if not root.is_dir():
        return None
    for folder in sorted(root.iterdir()):
        target = folder / "onnx_int8"
        if not target.is_dir():
            continue
        if all((target / name).is_file() for name in INT8_FILES):
            return target
    return None


def int8_installed() -> bool:
    """Bản cài đã có đủ bộ file INT8 chưa."""
    return int8_dir() is not None


# ── Kiểm tra bộ cài ─────────────────────────────────────────────────────────

def verify_bundle(precision: str = "fp32") -> list[str]:
    """Danh sách file model còn thiếu (rỗng = bộ cài đầy đủ).

    ``precision`` = "int8" thì kiểm thêm thư mục ``onnx_int8``.
    Dùng để báo lỗi rõ ràng thay cho thông báo mạng của huggingface_hub.
    """
    missing: list[str] = []

    marker = _cache_dir().parent / "voice.json"
    if not marker.is_file():
        missing.append("models/vieneu/voice.json")

    snap = _snapshot_dir()
    if snap is None:
        missing.append("models/vieneu/hf_cache/…/onnx_update/ (toàn bộ)")
        return missing

    for name in ROOT_FILES:
        if not (snap / name).is_file():
            missing.append(name)

    subfolder = "onnx_int8" if precision == "int8" else "onnx_update"
    names = INT8_FILES if precision == "int8" else FP32_FILES
    for name in names:
        if not (snap / subfolder / name).is_file():
            missing.append(f"{subfolder}/{name}")

    return missing


def bundle_ok(precision: str = "fp32") -> bool:
    return not verify_bundle(precision)


# ── Năng lực CPU ─────────────────────────────────────────────────────────────

def cpu_features() -> dict:
    """Best-effort: co CPU ho tro VNNI (can cho INT8) hay khong.

    - Linux   : doc /proc/cpuinfo
    - macOS   : `sysctl -n machdep.cpu.features` / `machdep.cpu.leaf7_features`
    - Windows : khong doc duoc -> known=False (UI canh bao nguoi dung)
    """
    info = {"known": False, "avx2": False, "avx512": False, "vnni": False,
            "name": platform.processor() or platform.machine()}
    try:
        if sys.platform.startswith("linux"):
            text = Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="ignore")
            flags = ""
            for line in text.splitlines():
                if line.lower().startswith("flags") and not flags:
                    flags = line.split(":", 1)[-1].lower()
            if flags:
                info["known"] = True
                info["avx2"] = "avx2" in flags
                info["avx512"] = "avx512f" in flags
                info["vnni"] = "avx512_vnni" in flags or "avx_vnni" in flags
            return info
        if sys.platform == "darwin":
            out = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.leaf7_features"],
                capture_output=True, text=True,
            ).stdout.lower()
            out2 = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.features"],
                capture_output=True, text=True,
            ).stdout.lower()
            combined = out + " " + out2
            if combined.strip():
                info["known"] = True
                info["avx2"] = "avx2" in combined
                info["avx512"] = "avx512f" in combined
                info["vnni"] = "avx512vnni" in combined.replace("_", "")
            return info
    except Exception:
        pass
    return info


def int8_recommendation() -> str:
    """Cau hoi ngan cho nguoi dung ve viec bat INT8."""
    feats = cpu_features()
    name = feats.get("name") or "CPU"
    if not feats["known"]:
        return (f"Không đọc được cờ CPU của máy này ({name}). INT8 cần CPU có "
                "VNNI (Intel thế hệ 11+/AMD Zen 3+); nếu không, hãy thử và nghe "
                "thử trước khi dùng lâu.")
    if feats["vnni"]:
        return f"CPU hỗ trợ VNNI ({name}) — dùng INT8 được."
    return (f"CPU không có VNNI ({name}). INT8 có thể tạo tiếng nhiễu — nên giữ "
            "FP32 trên máy này.")
