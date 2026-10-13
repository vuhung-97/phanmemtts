"""Tải mô hình TTS tiếng Việt offline vào thư mục models/ (Plug-and-Play)."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from huggingface_hub import hf_hub_download

BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"

KOKORO_REPO = "contextboxai/Kokoro-Vietnamese"
KOKORO_DIR = "kokoro_vi"
KOKORO_ONNX = "kokoro_vi.onnx"
KOKORO_VOICES = [
    "diem_trinh", "hung_thinh", "mai_linh", "mai_loan", "manh_dung",
    "my_yen", "ngoc_huyen", "phat_tai", "thanh_dat", "thuc_trinh",
    "tuan_ngoc", "duc_an", "duc_duy",
]


def _download_kokoro() -> Path:
    """Model Kokoro-Vietnamese cao cấp (~320MB, 24kHz, 13 giọng)."""
    folder = MODELS_DIR / KOKORO_DIR
    if (folder / KOKORO_ONNX).exists() and (folder / "voices.json").exists():
        return folder
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "voicepacks").mkdir(exist_ok=True)
    print(f"[..] Dang tai model Kokoro-Vietnamese {KOKORO_REPO} (len ~320MB) ...")
    for fname in (KOKORO_ONNX, "config.json", "voices.json"):
        path = Path(hf_hub_download(KOKORO_REPO, fname, local_dir=str(folder),
                                    local_dir_use_symlinks=False))
        target = folder / fname
        if path.resolve() != target.resolve():
            shutil.move(str(path), str(target))
        print(f"[OK] {fname}")
    for voice in KOKORO_VOICES:
        rel = f"voicepacks/{voice}.pt"
        path = Path(hf_hub_download(KOKORO_REPO, rel, local_dir=str(folder),
                                    local_dir_use_symlinks=False))
        target = folder / rel
        if path.resolve() != target.resolve():
            shutil.move(str(path), str(target))
    print(f"[OK] {len(KOKORO_VOICES)} voicepack -> {folder}")
    return folder


def _ensure_vieneu() -> Path:
    """Tao marker + tai model VieNeu vao models/vieneu/hf_cache (du an, khong phai C:)."""
    folder = MODELS_DIR / "vieneu"
    folder.mkdir(parents=True, exist_ok=True)
    marker = folder / "voice.json"
    if not marker.exists():
        meta = {
            "display_name": "VieNeu v3 Turbo",
            "language": "vi",
            "engine": "vieneu",
            "source": "pnnbao-ump/VieNeu-TTS-v3-Turbo",
        }
        marker.write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                          encoding="utf-8")
        print(f"[OK] VieNeu marker -> {marker}")

    hf_cache = folder / "hf_cache"
    hf_cache.mkdir(parents=True, exist_ok=True)
    # Dat cache truoc khi import vieneu de model ve du an, khong ve C:
    import os

    os.environ["HF_HUB_CACHE"] = str(hf_cache)

    print("[..] Dang tai model VieNeu v3 Turbo (lan dau ~494MB, sau do offline) ...")
    from vieneu import Vieneu

    tts = Vieneu()  # tu dong tai model vao HF_HUB_CACHE
    voices = tts.list_preset_voices()
    print(f"[OK] VieNeu san sang — {len(voices)} giuong preset, cache: {hf_cache}")
    return folder


def main() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    _download_kokoro()
    _ensure_vieneu()
    print("\n[HOAN TAT] Tat ca model da san sang trong:", MODELS_DIR)


if __name__ == "__main__":
    main()
