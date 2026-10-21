from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR_NAME = "PhanMemTTS"


def is_frozen() -> bool:
    return getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS")


def app_dir() -> Path:
    """Thu muc chua EXE khi frozen, thu muc source khi dev.

    Ghi file cau hinh / model tai day (ghi duoc), khong ghi vao _MEIPASS.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    """Thu muc du lieu ghi duoc theo tung nguoi dung.

    - Windows : %LOCALAPPDATA%\\PhanMemTTS
    - macOS   : ~/Library/Application Support/PhanMemTTS
    - Linux   : ~/.local/share/PhanMemTTS (hoac $XDG_DATA_HOME)

    Dung cho cau hinh, lich su, tu dien, audio tam — nhung thu KHONG nen nam
    canh EXE (tren Linux/macOS thu muc cai dat thuong khong ghi duoc).
    """
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))
    folder = base / APP_DIR_NAME
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError:
        # Khong ghi duoc (VD thu muc read-only) -> lui ve thu muc tam
        import tempfile

        folder = Path(tempfile.gettempdir()) / APP_DIR_NAME
        folder.mkdir(parents=True, exist_ok=True)
    return folder


def resource_path(rel: str) -> Path:
    """File read-only bundle trong EXE (logo, json mau).

    Khi frozen doc tu sys._MEIPASS, khi dev doc tu source.
    """
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / rel
    return app_dir() / rel
