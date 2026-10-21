# -*- coding: utf-8 -*-
"""Sinh voice_config.json cho ban phat hanh: bat TAT ca giong (preset + tu chinh)."""
import json
import sys

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.vieneu_engine import PRESET_VOICES, VieneuTTS  # noqa: E402

enabled = [f"vieneu:{vid}" for _label, vid in PRESET_VOICES]
enabled += [f"vieneu:{name}" for name in VieneuTTS.list_custom_voice_names()]

target = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "models" / "voice_config.json"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps({"enabled": enabled}, ensure_ascii=False, indent=2),
                  encoding="utf-8")
print(f"ghi {target} ({len(enabled)} giong)")
