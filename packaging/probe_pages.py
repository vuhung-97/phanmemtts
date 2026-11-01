"""Probe P1: các page Cài đặt / Từ điển / Giọng đọc / Bản quyền.

Chạy: .venv\\Scripts\\python.exe packaging\\probe_pages.py
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

_TMP = Path(tempfile.mkdtemp(prefix="ppmitts_pages_"))
os.environ["LOCALAPPDATA"] = str(_TMP)

from core import dictionary                    # noqa: E402
from core.licensing import store               # noqa: E402
from ui.config import load_settings            # noqa: E402
from ui.main_window import MainWindow          # noqa: E402
from ui.ui_kit import Card                     # noqa: E402


def pump(app, seconds: float = 0.3) -> None:
    end = time.time() + seconds
    while time.time() < end:
        app.update()
        time.sleep(0.02)


def main() -> int:
    ok = True
    store.configure(_TMP / "license", registry=False)
    app = MainWindow()
    if getattr(app, "_prompt_job", None):
        app.after_cancel(app._prompt_job)
    app.geometry("1280x800")
    pump(app, 0.6)

    # ── 1. Đăng ký page ──
    ids = ("settings", "dictionary", "voices", "license")
    print("[page] co mat:", {pid: app.shell.has_page(pid) for pid in ids})
    for pid in ids:
        if not app.shell.has_page(pid):
            print(f"[page] LOI: thieu page {pid}")
            ok = False

    # ── 2. Cài đặt ──
    app.shell.show("settings")
    pump(app)
    sp = app.settings_page
    sp.storage_combo.set("Luôn ghi file tạm (bài dài không tốn RAM)")
    sp.precision_combo.set("FP32 — chất lượng cao (mặc định)")
    sp._mark_dirty()
    pump(app, 0.1)
    print("[settings] badge:", sp._badge.cget("text"),
          "| mapped:", sp._badge.winfo_ismapped())
    if sp._badge.cget("text") != "Chưa lưu":
        print("[settings] LOI: khong hien badge chua luu")
        ok = False
    sp._save()
    pump(app, 0.2)
    saved = load_settings()
    print("[settings] storage:", saved["storage"], "| status:",
          sp.status_label.cget("text"))
    if saved["storage"] != "disk":
        print("[settings] LOI: khong luu storage")
        ok = False

    # ── 3. Từ điển ──
    app.shell.show("dictionary")
    pump(app)
    dp = app.dictionary_page
    dp.src_entry.delete(0, "end")
    dp.src_entry.insert(0, "KTX")
    dp.dst_entry.delete(0, "end")
    dp.dst_entry.insert(0, "ký túc xá")
    dp._save_entry()
    pump(app, 0.2)
    entries = dictionary.load()["entries"]
    print("[dict] so muc:", len(entries),
          "| count label:", dp.count_label.cget("text"))
    if not entries or entries[0]["from"] != "KTX":
        print("[dict] LOI: khong luu muc")
        ok = False

    # ── 4. Giọng đọc ──
    app.shell.show("voices")
    pump(app, 0.4)
    vp = app.voices_page
    total = len(vp._checkboxes)
    print("[voices] tong giong:", total, "| count:", vp.count_label.cget("text"))
    if total < 20:
        print("[voices] LOI: thieu giong")
        ok = False
    vp._select_all()
    vp._save()
    pump(app, 0.2)
    print("[voices] save:", vp.status_label.cget("text"))

    # ── 5. Bản quyền ──
    app.shell.show("license")
    pump(app)
    lp = app.license_page
    print("[license] badge:", lp._badge.cget("text"),
          "| may:", lp.machine_label.cget("text"),
          "| nut:", lp.activate_btn.cget("text"))
    if "kích hoạt" not in lp._badge.cget("text").lower():
        print("[license] LOI: trang thai sai")
        ok = False

    # ── 6. Không mở dialog khi điều hướng ──
    toplevels = [w for w in app.winfo_children()
                 if w.winfo_class() == "Toplevel"]
    print("[nav] so dialog mo:", len(toplevels))
    if toplevels:
        print("[nav] LOI: van mo dialog thay vi page")
        ok = False

    # ── 6b. Hàng loạt: hai cột cùng co giãn ──
    app.shell.show("batch")
    pump(app, 0.2)
    bp = app.batch_page
    widths = []
    for size in (1024, 1280, 1440):
        app.geometry(f"{size}x800")
        pump(app, 0.2)
        children = bp.body.winfo_children()
        left_w = children[0].winfo_width()
        right_w = children[1].winfo_width()
        widths.append((size, left_w, right_w))
        share = right_w / max(1, left_w + right_w)
        print(f"[batch] {size}: trai={left_w} phai={right_w} ({share:.0%})")
        if left_w < 280 or right_w < 240:
            print("[batch] LOI: cot qua hep")
            ok = False
        if not (0.30 <= share <= 0.48):
            print("[batch] LOI: ti le cot sai")
            ok = False

    # ── 7. Padding trong Card ──
    def walk(widget):
        for child in widget.winfo_children():
            yield child
            yield from walk(child)

    issues = []
    for page_id in ids + ("text", "batch", "history"):
        if not app.shell.has_page(page_id):
            continue
        app.shell.show(page_id)
        pump(app, 0.15)
        page = app.shell.current_page
        for card in walk(page):
            if not isinstance(card, Card) or not card.winfo_ismapped():
                continue
            x0, y0 = card.winfo_rootx(), card.winfo_rooty()
            x1 = x0 + card.winfo_width()
            y1 = y0 + card.winfo_height()
            for child in card.content.winfo_children():
                if not child.winfo_ismapped():
                    continue
                cx0, cy0 = child.winfo_rootx(), child.winfo_rooty()
                cx1, cy1 = cx0 + child.winfo_width(), cy0 + child.winfo_height()
                gaps = (cx0 - x0, cy0 - y0, x1 - cx1, y1 - cy1)
                if min(gaps) < 8:
                    issues.append((page_id, child.__class__.__name__, gaps))
    print("[padding] widget sat vien (<8px):", len(issues))
    for issue in issues[:5]:
        print("   ", issue)
    if issues:
        print("[padding] LOI: noi dung dinh vien the")
        ok = False

    app.destroy()
    print("\nKẾT QUẢ:", "OK" if ok else "LỖI", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
