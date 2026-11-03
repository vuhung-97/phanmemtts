"""Probe: trạng thái PlayerBar khi chuyển tab + tốc độ Hội thoại.

Chạy: .venv\\Scripts\\python.exe packaging\\probe_tab_state.py
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

_TMP = Path(tempfile.mkdtemp(prefix="ppmitts_tabstate_"))
os.environ["LOCALAPPDATA"] = str(_TMP)

from core.licensing import fingerprint, guard, shortcode, store  # noqa: E402
from ui.main_window import MainWindow                              # noqa: E402

TEXT = "Xin chào. Đây là câu thứ hai. Và câu thứ ba."
SCRIPT = "An: Một câu.\nBình: Hai câu.\nAn: Ba câu."


def pump(app, seconds: float = 0.3) -> None:
    end = time.time() + seconds
    while time.time() < end:
        app.update()
        time.sleep(0.02)


def main() -> int:
    ok = True
    store.configure(_TMP / "license", registry=False)
    guard.reset_cache()
    guard.install(shortcode.issue(fingerprint.machine24(),
                                  shortcode.KIND_LIFETIME), now=time.time())

    app = MainWindow()
    if getattr(app, "_prompt_job", None):
        app.after_cancel(app._prompt_job)
    app.geometry("1280x800")
    pump(app, 0.8)
    bar = app.shell.player_bar

    def state() -> tuple[float, float, str]:
        return (bar._duration, bar.waveform._duration,
                bar.time_label.cget("text"))

    # ── Văn bản có audio ──
    app.textbox.set_text(TEXT)
    app._start_convert()
    deadline = time.time() + 180
    while app._busy and time.time() < deadline:
        app.update()
        time.sleep(0.05)
    pump(app, 0.4)
    text_dur = app._timeline.total_duration
    print("[text] duration:", round(text_dur, 2), "| bar:", state())
    if abs(bar._duration - text_dur) > 0.05:
        print("[text] LOI: bar khong khop duration")
        ok = False

    # ── Hội thoại chưa có audio -> phải clear, không dính thời gian tab văn bản ──
    app.shell.show("dialogue")
    pump(app, 0.3)
    print("[dialogue rong] bar:", state())
    if bar._duration != 0.0:
        print("[dialogue rong] LOI: chua clear trang thai tab truoc")
        ok = False

    # ── Tạo hội thoại ──
    page = app.dialogue_page
    page.editor.set_text(SCRIPT)
    page._parse()
    page._create()
    deadline = time.time() + 180
    while page._busy and time.time() < deadline:
        app.update()
        time.sleep(0.05)
    pump(app, 0.5)
    dlg_dur = page._timeline.total_duration
    print("[dialogue] duration:", round(dlg_dur, 2), "| bar:", state())
    if abs(bar._duration - dlg_dur) > 0.05:
        print("[dialogue] LOI: bar khong khop duration")
        ok = False

    # ── Chuyển tab qua lại 2 vòng ──
    for index in range(2):
        app.shell.show("text")
        pump(app, 0.3)
        got_text = state()
        print(f"[switch {index}] text ->", got_text)
        if abs(bar._duration - text_dur) > 0.05:
            print("[switch] LOI: thoi luong van ban sai")
            ok = False
        app.shell.show("dialogue")
        pump(app, 0.3)
        got_dlg = state()
        print(f"[switch {index}] dialogue ->", got_dlg)
        if abs(bar._duration - dlg_dur) > 0.05:
            print("[switch] LOI: thoi luong hoi thoai sai")
            ok = False
        if got_text[2] == got_dlg[2] and abs(text_dur - dlg_dur) > 0.2:
            print("[switch] LOI: dong ho thoi gian khong doi theo tab")
            ok = False

    # ── Tốc độ Hội thoại áp dụng ngay ──
    base = page._timeline.total_duration
    page._on_speed_change(1.5)
    deadline = time.time() + 60
    while page._speed_applying and time.time() < deadline:
        app.update()
        time.sleep(0.05)
    pump(app, 0.3)
    fast = page._timeline.total_duration
    print("[speed] 1.0 -> 1.5:", round(base, 2), "->", round(fast, 2),
          "| bar:", round(bar._duration, 2), "| combo:", bar.speed_combo.get())
    if abs(fast - base / 1.5) > 0.25:
        print("[speed] LOI: hoi thoai khong doi toc do")
        ok = False
    if abs(bar._duration - fast) > 0.05:
        print("[speed] LOI: bar khong cap nhat sau khi doi toc do")
        ok = False

    page._on_speed_change(1.0)
    deadline = time.time() + 60
    while page._speed_applying and time.time() < deadline:
        app.update()
        time.sleep(0.05)
    pump(app, 0.3)
    back = page._timeline.total_duration
    print("[speed] ve 1.0:", round(back, 2))
    if abs(back - base) > 0.25:
        print("[speed] LOI: khong tra ve toc do goc")
        ok = False

    app.destroy()
    print("\nKẾT QUẢ:", "OK" if ok else "LỖI", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
