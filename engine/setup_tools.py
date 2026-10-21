"""Tien ich cai dat / kiem tra mo truong: model INT8, GPU, nang luc CPU.

Tach rieng khoi engine/vieneu_engine.py de phan sinh audio khong bi
phu thuoc vao viec tai model hay pip install.
"""

from __future__ import annotations

import contextlib
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Callable

MODEL_REPO = "pnnbao-ump/VieNeu-TTS-v3-Turbo"

# Cac file can co trong cache de chay duoc INT8 (7 file, ~158 MB).
INT8_FILES = (
    "config.json",
    "tokenizer.json",
    "vieneu_acoustic_cached.onnx",
    "vieneu_backbone_shared.data",
    "vieneu_decode_step.onnx",
    "vieneu_prefill.onnx",
    "vieneu_v3_heads.npz",
)

Progress = Callable[[str], None]


# ── Cửa sổ cho phép gọi mạng ────────────────────────────────────────────────

@contextlib.contextmanager
def online_window():
    """Tạm cho phép gọi mạng tới Hugging Face.

    App đặt HF_HUB_OFFLINE=1 để luôn chạy offline. Nhưng huggingface_hub đọc
    biến này LÚC IMPORT (huggingface_hub.constants.HF_HUB_OFFLINE) nên chỉ sửa
    os.environ là không đủ — phải sửa cả hằng số trong module.
    """
    import huggingface_hub.constants as hf_constants

    old_env = os.environ.get("HF_HUB_OFFLINE")
    old_const = hf_constants.HF_HUB_OFFLINE
    os.environ["HF_HUB_OFFLINE"] = "0"
    hf_constants.HF_HUB_OFFLINE = False
    try:
        yield
    finally:
        hf_constants.HF_HUB_OFFLINE = old_const
        if old_env is None:
            os.environ.pop("HF_HUB_OFFLINE", None)
        else:
            os.environ["HF_HUB_OFFLINE"] = old_env


# ── Model INT8 ────────────────────────────────────────────────────────────────

def _cache_dir() -> Path:
    from engine.vieneu_engine import HF_CACHE_DIR

    return HF_CACHE_DIR


def _snapshot_root() -> Path:
    return (_cache_dir()
            / f"models--{MODEL_REPO.replace('/', '--')}" / "snapshots")


def int8_dir() -> Path | None:
    """Thư mục chứa đủ bộ file INT8 trong cache (None nếu thiếu)."""
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
    """Đã có đủ bộ file INT8 trong cache chưa."""
    return int8_dir() is not None


def download_int8(progress: Progress | None = None) -> None:
    """Tải bộ graph INT8 (~158 MB) vào cache của app.

    Ném RuntimeError với thông báo rõ ràng nếu tải không thành công —
    không được báo "thành công" khi thực tế không tải được gì.
    """
    from huggingface_hub import snapshot_download

    if progress:
        progress("Đang tải model INT8 (158 MB)...")

    try:
        with online_window():
            snapshot_download(
                repo_id=MODEL_REPO,
                allow_patterns=["onnx_int8/*"],
                cache_dir=str(_cache_dir()),
                max_workers=2,
            )
    except Exception as exc:
        raise RuntimeError(
            "Không tải được model INT8 — cần kết nối Internet (chỉ cần một lần). "
            f"Chi tiết: {exc}"
        ) from exc

    # Kiểm chứng thật sự có đủ file (tránh báo thành công giả)
    if not int8_installed():
        raise RuntimeError(
            "Tải xong nhưng không tìm thấy file INT8 trong cache. "
            "Hãy thử lại, hoặc dùng FP32 (mặc định)."
        )

    if progress:
        progress("Đã tải xong model INT8 (158 MB).")


# ── GPU ──────────────────────────────────────────────────────────────────────

def gpu_status() -> tuple[bool, str]:
    """(cuda_available, message) — trạng thái backend PyTorch/CUDA."""
    try:
        import torch
    except Exception:
        return False, "Chưa cài PyTorch — app đang chạy ONNX/CPU."
    try:
        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            return True, f"GPU sẵn sàng: {name}"
    except Exception:
        pass
    return False, "PyTorch đã cài nhưng không thấy GPU CUDA khả dụng."


def install_gpu_support(progress: Progress | None = None) -> None:
    """Cai PyTorch ban CUDA (vai GB) — can restart app sau khi xong."""
    index_url = "https://download.pytorch.org/whl/cu128"
    cmd = [
        sys.executable, "-m", "pip", "install", "torch==2.8.0",
        "--index-url", index_url,
    ]
    if progress:
        progress("Đang tải PyTorch CUDA (~3 GB)...")
    proc = subprocess.run(
        cmd, capture_output=True, text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0,
    )
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-6:]
        raise RuntimeError("\n".join(tail) or "Cài PyTorch thất bại.")
    if progress:
        progress("Đã cài PyTorch CUDA — hãy khởi động lại app.")


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
