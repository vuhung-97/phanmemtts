"""Probe: scroll dự phòng của Page khi cửa sổ nhỏ.

Kiểm tra:
- Mọi page dùng ScrollArea cho body.
- Khi nội dung vừa khung: không widget nào bị cắt, thanh cuộn ẩn.
- Khi thiếu chỗ (Settings/Bản quyền @1024x640, Hàng loạt @900x560):
  thanh cuộn hiện và cuộn tới cuối thấy được nội dung.
- Không có vòng lặp layout khi rảnh.

Chạy: .venv\\Scripts\\python.exe packaging\\probe_scroll.py
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

_TMP = Path(tempfile.mkdtemp(prefix="ppmitts_scroll_"))
os.environ["LOCALAPPDATA"] = str(_TMP)

import customtkinter as ctk                         # noqa: E402

from core.licensing import store                    # noqa: E402
from ui.main_window import MainWindow                # noqa: E402
from ui.ui_kit import ScrollArea                     # noqa: E402

PAGES = ("text", "dialogue", "merge", "batch", "history",
         "dictionary", "voices", "settings", "license")

# Page cần cuộn ở 1024x640 (các page khác tự co giãn vừa khung).
NEED_SCROLL_640 = {"settings", "license"}


def pump(app, seconds: float = 0.3) -> None:
    end = time.time() + seconds
    while time.time() < end:
        app.update()
        time.sleep(0.01)


def _host(widget):
    if isinstance(widget, ctk.CTkScrollableFrame):
        return widget._parent_frame
    return widget


def clipped(page) -> tuple | None:
    """Widget đầu tiên lòi khỏi khung nhìn (bỏ qua nội dung cuộn nội bộ)."""
    canvas = page.body._parent_canvas
    left = canvas.winfo_rootx()
    top = canvas.winfo_rooty()
    vw, vh = canvas.winfo_width(), canvas.winfo_height()
    stack = list(page.body.winfo_children())
    while stack:
        widget = stack.pop()
        if not widget.winfo_ismapped():
            continue
        host = _host(widget)
        x = host.winfo_rootx() - left
        y = host.winfo_rooty() - top
        if y + host.winfo_height() > vh + 2 or x + host.winfo_width() > vw + 2:
            return (widget.__class__.__name__, x, y,
                    host.winfo_width(), host.winfo_height())
        if isinstance(widget, ctk.CTkScrollableFrame):
            continue  # vùng cuộn lồng: nội dung dài là cố ý
        stack.extend(widget.winfo_children())
    return None


def bottom_visible(page) -> bool:
    canvas = page.body._parent_canvas
    last = page.body.winfo_children()[-1]
    return (last.winfo_rooty() + last.winfo_height()
            <= canvas.winfo_rooty() + canvas.winfo_height() + 2)


def check_page(app, shell, page_id: str, want_bar: bool, ok: bool) -> bool:
    shell.show(page_id)
    pump(app, 0.3)
    page = shell.current_page
    if not isinstance(page.body, ScrollArea):
        print(f"[scroll] {page_id}: LOI - body khong phai ScrollArea")
        return False
    bar = page.body.scrollbar_visible
    print(f"[scroll] {app.winfo_width()}x{app.winfo_height()} {page_id:10s} "
          f"bar={bar} inner={page.body.winfo_height()} "
          f"req={page.body.winfo_reqheight()}", flush=True)
    if bar is not want_bar:
        print(f"[scroll] {page_id}: LOI - thanh cuon phai la {want_bar}")
        ok = False
    if bar:
        page.body.scroll_to_bottom()
        pump(app, 0.12)
        if not bottom_visible(page):
            print(f"[scroll] {page_id}: LOI - khong cuon toi cuoi duoc")
            ok = False
        page.body.scroll_to_top()
    else:
        bad = clipped(page)
        if bad is not None:
            print(f"[scroll] {page_id}: LOI - noi dung bi cat {bad}")
            ok = False
    return ok


def main() -> int:
    ok = True
    store.configure(_TMP / "license", registry=False)

    calls = {"n": 0}
    original_apply = ScrollArea._apply

    def counted(self):
        calls["n"] += 1
        return original_apply(self)

    ScrollArea._apply = counted

    app = MainWindow()
    job = getattr(app, "_prompt_job", None)
    if job:
        try:
            app.after_cancel(job)
        except Exception:
            pass
    app.geometry("1280x800")
    pump(app, 0.6)
    shell = app.shell

    # ── 1. Mọi page đều có ScrollArea ──
    for pid in PAGES:
        if not isinstance(shell._pages[pid].body, ScrollArea):
            print(f"[scroll] LOI: {pid} khong dung ScrollArea")
            ok = False

    # ── 2. 1280x800: đủ chỗ, không thanh cuộn ──
    for pid in PAGES:
        ok = check_page(app, shell, pid, False, ok)

    # ── 3. 1024x700 và 1024x640 ──
    for width, height in ((1024, 700), (1024, 640)):
        app.geometry(f"{width}x{height}")
        pump(app, 0.5)
        for pid in PAGES:
            want = pid in NEED_SCROLL_640
            ok = check_page(app, shell, pid, want, ok)

    # ── 4. Dưới min size: fallback vẫn hoạt động (Hàng loạt) ──
    app.minsize(800, 500)
    app.geometry("900x560")
    pump(app, 0.5)
    ok = check_page(app, shell, "batch", True, ok)

    # ── 5. Không lặp layout khi rảnh ──
    before = calls["n"]
    pump(app, 0.8)
    idle = calls["n"] - before
    print(f"[scroll] so lan layout khi ranh: {idle}", flush=True)
    if idle > 2:
        print("[scroll] LOI: lap layout lien tuc khi ranh")
        ok = False

    app.destroy()
    print("\nKẾT QUẢ:", "OK" if ok else "LỖI", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
