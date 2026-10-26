"""Tạo build/keygen.ico từ logo/logo.jpg (dùng cho PyInstaller)."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "logo" / "logo.jpg"
DST = ROOT / "build" / "keygen.ico"


def main() -> int:
    if not SRC.is_file():
        print(f"[LOI] Không thấy {SRC}")
        return 1
    DST.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(SRC) as image:
        rgba = image.convert("RGBA")
        rgba.save(DST, sizes=[(256, 256), (128, 128), (64, 64),
                              (48, 48), (32, 32), (16, 16)])
    print(f"[OK] {DST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
