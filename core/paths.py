from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS")


def app_dir() -> Path:
    """Thu muc chua EXE khi frozen, thu muc source khi dev.

    Ghi file cau hinh / model tai day (ghi duoc), khong ghi vao _MEIPASS.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resource_path(rel: str) -> Path:
    """File read-only bundle trong EXE (logo, json mau).

    Khi frozen doc tu sys._MEIPASS, khi dev doc tu source.
    """
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / rel
    return app_dir() / rel
