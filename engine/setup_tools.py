"""Tien ich cai dat / kiem tra mo truong: model INT8, GPU, nang luc CPU.

Tach rieng khoi engine/vieneu_engine.py de phan sinh audio khong bi
phu thuoc vao viec tai model hay pip install.
"""

from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path
from typing import Callable

MODEL_REPO = "pnnbao-ump/VieNeu-TTS-v3-Turbo"

Progress = Callable[[str], None]


# ── Model INT8 ────────────────────────────────────────────────────────────────

def _cache_dir() -> Path:
    from engine.vieneu_engine import HF_CACHE_DIR

    return HF_CACHE_DIR


def int8_installed() -> bool:
    """Da co bo graph INT8 (onnx_int8/) trong cache chua."""
    cache = _cache_dir()
    if not cache.exists():
        return False
    for folder in cache.glob(f"models--{MODEL_REPO.replace('/', '--')}/snapshots/*"):
        if (folder / "onnx_int8").is_dir():
            return True
    return False


def download_int8(progress: Progress | None = None) -> None:
    """Tai bo graph INT8 (~1/4 dung luong fp32) vao cache cua app."""
    from huggingface_hub import snapshot_download

    def _cb(_percent) -> None:
        if progress:
            progress("Đang tải model INT8...")

    snapshot_download(
        repo_id=MODEL_REPO,
        allow_patterns=["onnx_int8/*"],
        cache_dir=str(_cache_dir()),
        max_workers=2,
    )
    if progress:
        progress("Đã tải xong model INT8.")


# ── GPU ──────────────────────────────────────────────────────────────────────

def gpu_status() -> tuple[bool, str]:
    """(cuda_available, message) — trang thai backend PyTorch/CUDA."""
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
    if not feats["known"]:
        return ("Không đọc được thông tin CPU. INT8 cần CPU hỗ trợ VNNI "
                "(Intel thế hệ 11+/AMD Zen 3+); nếu không, hãy thử và nghe thử "
                "trước khi dùng lâu.")
    if feats["vnni"]:
        return "CPU hỗ trợ VNNI — dùng INT8 được."
    return ("CPU không có VNNI. INT8 có thể tạo tiếng nhiễu — nên giữ FP32 "
            "trên máy này.")
