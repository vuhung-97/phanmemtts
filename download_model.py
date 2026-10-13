"""Tải mô hình TTS tiếng Việt offline vào thư mục models/ (Plug-and-Play)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"


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

    # File rieng cho cloning giong (lazy-load, chi can khi tao giong moi) — tai truoc 1 lan
    from huggingface_hub import hf_hub_download
    for fn in ("speaker_encoder.onnx", "denoiser.onnx"):
        hf_hub_download("pnnbao-ump/VieNeu-TTS-v3-Turbo", fn)
    print("[OK] speaker_encoder.onnx + denoiser.onnx san sang (tao giong)")
    return folder


def main() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    _ensure_vieneu()
    print("\n[HOAN TAT] Tat ca model da san sang trong:", MODELS_DIR)


if __name__ == "__main__":
    main()
