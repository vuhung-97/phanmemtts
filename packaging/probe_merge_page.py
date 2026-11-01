"""Probe P3: trang Ghép nhạc (preview + xuất file + giữ trạng thái).

Chạy: .venv\\Scripts\\python.exe packaging\\probe_merge_page.py
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_TMP = Path(tempfile.mkdtemp(prefix="ppmitts_merge_"))
os.environ["LOCALAPPDATA"] = str(_TMP)

import numpy as np
import soundfile as sf

from core.licensing import fingerprint, guard, shortcode, store  # noqa: E402
from ui.main_window import MainWindow                             # noqa: E402


def pump(app, seconds: float) -> None:
    end = time.time() + seconds
    while time.time() < end:
        app.update()
        time.sleep(0.02)


def make_wav(path: Path, seconds: float = 1.0, freq: float = 440.0) -> None:
    sr = 48000
    t = np.linspace(0, seconds, int(sr * seconds), endpoint=False)
    wave = (0.3 * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    sf.write(path, wave, sr)


def main() -> int:
    ok = True
    store.configure(_TMP / "license", registry=False)
    guard.reset_cache()
    guard.install(shortcode.issue(fingerprint.machine24(),
                                  shortcode.KIND_LIFETIME), now=time.time())

    voice = _TMP / "voice.wav"
    intro = _TMP / "intro.wav"
    make_wav(voice, 1.0, 440.0)
    make_wav(intro, 0.5, 220.0)

    app = MainWindow()
    if getattr(app, "_prompt_job", None):
        app.after_cancel(app._prompt_job)
    app.geometry("1280x800")
    pump(app, 0.8)

    if not app.shell.has_page("merge"):
        print("LOI: chua dang ky page merge")
        return 1
    app.shell.show("merge")
    pump(app, 0.3)
    page = app.merge_page
    print("[page] hien tai:", app.shell.current_page.page_id)

    # ── Thêm file gốc ──
    page._add_voice(str(voice))
    pump(app, 0.5)
    print("[voice] so doan:", len(page._voice_paths),
          "| thoi luong:", page._voice_durations)

    # ── Preview dùng player chung ──
    page._preview()
    deadline = time.time() + 60
    while page._busy and time.time() < deadline:
        app.update()
        time.sleep(0.05)
    pump(app, 0.3)
    bar = app.shell.player_bar
    duration_text = bar.time_label.cget("text")
    transport = str(bar.toggle_btn.cget("state"))
    print("[preview] active:", page._preview_active, "| bar:", duration_text,
          "| transport:", transport)
    if not page._preview_active or "00:00 / 00:00" in duration_text:
        print("[preview] LOI: khong phat duoc ban nghe thu")
        ok = False
    if transport != "normal":
        print("[preview] LOI: transport khong bat")
        ok = False
    if str(bar.speed_combo.cget("state")) != "disabled":
        print("[preview] LOI: toc do phai bi khoa o trang ghep nhac")
        ok = False

    # ── Xuất file ──
    out = _TMP / "merged.mp3"
    config = page._build_config()
    page._merge_worker(config, str(out))
    deadline = time.time() + 60
    while time.time() < deadline:
        pump(app, 0.2)
        if out.exists() and out.stat().st_size > 0:
            break
    size = out.stat().st_size if out.exists() else 0
    print("[export] file:", out.name, size, "bytes")
    if size <= 0:
        print("[export] LOI: khong tao duoc file")
        ok = False

    # ── Chuyển trang qua lại ──
    app.shell.show("text")
    pump(app, 0.2)
    speed_text = str(app.shell.player_bar.speed_combo.cget("state"))
    app.shell.show("merge")
    pump(app, 0.2)
    print("[nav] giu file goc:", len(page._voice_paths),
          "| speed o text:", speed_text,
          "| speed o merge:", app.shell.player_bar.speed_combo.cget("state"))
    if len(page._voice_paths) != 1:
        print("[nav] LOI: mat file goc khi chuyen trang")
        ok = False
    if speed_text != "normal":
        print("[nav] LOI: khong tra lai toc do cho trang van ban")
        ok = False

    app.destroy()
    print("\nKẾT QUẢ:", "OK" if ok else "LỖI", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
