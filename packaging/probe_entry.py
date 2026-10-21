# -*- coding: utf-8 -*-
"""Probe đóng gói (console) — kiểm tra toàn bộ đường TTS trong môi trường frozen.

Dung y chang Analysis/hiddenimports voi app_v3.spec, chi khac console=True
va ten EXE, de chay TTS + xuat MP3 ma khong can mo GUI.

Chay: PhanMem..._test.exe
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:  # console Windows mac dinh la cp1252 -> khong in duoc tieng Viet co dau
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from engine.model_manager import ModelManager
from engine.tts_engine import TtsEngine
from audio import exporter

OUT = Path(__file__).resolve().parent / "probe_output.mp3"


def main() -> int:
    t0 = time.time()
    mm = ModelManager()
    models = mm.scan()
    print(f"[probe] so giong tim thay: {len(models)}")
    if not models:
        print("[probe] LOI: khong tim thay model nao")
        return 2
    model = models[4] if len(models) > 4 else models[0]
    print(f"[probe] chon giong: {model.display_name} ({model.model_id})")

    tts = mm.load_tts(model)
    engine = TtsEngine(tts)
    print(f"[probe] model nap xong sau {time.time() - t0:.1f}s, sr={engine.sample_rate}")

    audio, _ = engine.synthesize("Xin chao, day la ban goi thu nghiem goi am offline.")
    print(f"[probe] tong hop xong: {len(audio)} mau, {len(audio)/engine.sample_rate:.2f}s")

    out = exporter.export(audio, engine.sample_rate, str(OUT))
    print(f"[probe] xuat file: {out} ({Path(out).stat().st_size} bytes)")
    print("[probe] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
