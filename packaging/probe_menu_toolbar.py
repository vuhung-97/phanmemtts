"""Probe: menu bar kiểu Windows + panel phải (Chuyển đổi / Xuất file).

Kiểm tra:
- Chiều cao header / dải menu / khung soạn thảo ở 4 bề rộng cửa sổ.
- Nội dung 3 menu (Tệp / Công cụ / Trợ giúp), phím tắt, trạng thái khi bận.
- Nút Chuyển đổi ↔ Dừng, Xuất file bị khoá khi bận.
- Mục "Lịch sử bản dựng" mở được dialog.

Chạy: .venv\\Scripts\\python.exe packaging\\probe_menu_toolbar.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ui.main_window import MainWindow

WIDTHS = (980, 1100, 1200, 1440)
EXPECTED_HEADER = 176
EXPECTED_MENU = 30
EXPECTED_BODY = 146


def menu_commands(menu) -> list[tuple[str, str]]:
    """[(label, accelerator)] của các mục command (bỏ separator)."""
    last = menu.index("end")
    if last is None:
        return []
    return [
        (menu.entrycget(i, "label"), menu.entrycget(i, "accelerator"))
        for i in range(last + 1)
        if menu.type(i) == "command"
    ]


def pump(app, seconds: float) -> None:
    """Chạy vòng sự kiện (để các after(150/600/1500) của logo kịp chạy)."""
    end = time.time() + seconds
    while time.time() < end:
        app.update()
        time.sleep(0.02)


def main() -> int:
    ok = True
    app = MainWindow()
    if getattr(app, "_prompt_job", None):
        app.after_cancel(app._prompt_job)
    app.geometry("1200x740")
    app.update_idletasks()
    app.update()
    pump(app, 1.7)                      # logo co giãn theo layout xong
    tb = app.topbar

    # ── 1b. Không được dựng trùng widget (lỗi từng gặp: toolbar 2 lần) ──
    body_widgets = tb._body.winfo_children()
    bar = tb.menubar.winfo_children()[0]
    menu_buttons = [w for w in bar.winfo_children()
                    if w.winfo_class() in ("Frame", "Canvas")]
    print("[dup] body widgets =", len(body_widgets),
          "| menu buttons =", len(menu_buttons), flush=True)
    if len(body_widgets) != 6:
        print(f"[dup] LOI: than header co {len(body_widgets)} widget (mong doi 6)",
              flush=True)
        ok = False
    if len(menu_buttons) != 3:
        print(f"[dup] LOI: menu bar co {len(menu_buttons)} nut (mong doi 3)",
              flush=True)
        ok = False
    for name in ("convert_btn", "export_btn", "voice_combo", "speed_combo",
                 "test_btn", "status_label"):
        widget = getattr(tb, name, None)
        if widget is None or not widget.winfo_exists():
            print(f"[dup] LOI: thieu widget {name}", flush=True)
            ok = False

    # ── 1. Kích thước ở nhiều bề rộng ──
    print("[size] width | header | menu | body | textbox | o cau test", flush=True)
    for width in WIDTHS:
        app.geometry(f"{width}x740")
        app.update_idletasks()
        app.update()
        app.update()
        header = tb.winfo_height()
        menu_h = tb.menubar.winfo_height()
        body_h = tb._body.winfo_height()
        textbox_h = app.textbox.winfo_height()
        entry_w = tb.test_entry.winfo_width()
        print(f"[size] {width:5d} | {header:4d} | {menu_h:4d} | {body_h:4d} | "
              f"{textbox_h:4d} | {entry_w:4d}", flush=True)
        if header != EXPECTED_HEADER:
            print(f"[size] LOI: header {header} != {EXPECTED_HEADER}", flush=True)
            ok = False
        if menu_h != EXPECTED_MENU or body_h != EXPECTED_BODY:
            print("[size] LOI: dai menu / than panel sai chieu cao", flush=True)
            ok = False
        if textbox_h < 300:
            print(f"[size] LOI: khung soan thao qua thap ({textbox_h}px)", flush=True)
            ok = False
        if entry_w < 60:
            print("[size] LOI: o cau test bi co qua nho", flush=True)
            ok = False

    app.geometry("1200x740")
    app.update_idletasks()
    app.update()

    # ── 2. Panel phải: 2 nút hành động chính ──
    panel = tb.convert_btn.master.master
    print("[panel] convert h =", tb.convert_btn.winfo_height(),
          "| export h =", tb.export_btn.winfo_height(),
          "| panel w =", panel.winfo_width(), flush=True)
    if panel.winfo_width() < 150:
        print("[panel] LOI: panel phai hep qua", flush=True)
        ok = False
    if tb.convert_btn.winfo_height() <= tb.export_btn.winfo_height():
        print("[panel] LOI: nut Chuyen doi khong noi bat hon Xuat file", flush=True)
        ok = False

    # ── 3. Nội dung menu + phím tắt ──
    expected = {
        "file": ["Mở văn bản…", "Thoát"],
        "tools": ["Ghép nhạc", "Chuyển đổi hàng loạt…", "Lịch sử bản dựng",
                  "Từ điển phát âm…", "Làm sạch văn bản", "Cài đặt"],
        "help": ["Thông tin bản quyền", "Hướng dẫn sử dụng",
                 "Điều khoản sử dụng", "Giới thiệu"],
    }
    for key, labels in expected.items():
        items = menu_commands(tb.menus[key])
        names = [label for label, _ in items]
        print(f"[menu] {key}: {names}", flush=True)
        if names != labels:
            print(f"[menu] LOI: {key} mong doi {labels}", flush=True)
            ok = False
        for label, accel in items:
            if label in ("Mở văn bản…", "Lịch sử bản dựng", "Thoát") and not accel:
                print(f"[menu] LOI: thieu phim tat cho {label!r}", flush=True)
                ok = False

    shortcuts = {
        "<Control-o>": "Mo van ban",
        "<Control-h>": "Lich su",
        "<Alt-f>": "menu Tep",
        "<Alt-c>": "menu Cong cu",
        "<Alt-t>": "menu Tro giup",
    }
    for seq, label in shortcuts.items():
        if not app.bind(seq):
            print(f"[key] LOI: chua bind {seq} ({label})", flush=True)
            ok = False
    print("[key]", {seq: bool(app.bind(seq)) for seq in shortcuts}, flush=True)

    # ── 4. Bận / rảnh ──
    tools = tb.menus["tools"]
    tb.set_busy(True)
    app.update()
    busy = {
        "convert": tb.convert_btn.cget("text"),
        "merge": tools.entrycget(tb._merge_index, "state"),
        "history": tools.entrycget(tb._history_index, "state"),
        "settings": tools.entrycget(tb._settings_index, "state"),
        "export": tb.export_btn.cget("state"),
    }
    print("[busy]", busy, flush=True)
    if "Dừng" not in busy["convert"] or busy["export"] != "disabled":
        print("[busy] LOI: nut chinh khong chuyen sang Dung / khoa xuat", flush=True)
        ok = False
    if busy["merge"] != "disabled" or busy["settings"] != "disabled":
        print("[busy] LOI: menu Ghep nhac / Cai dat khong bi khoa", flush=True)
        ok = False
    if busy["history"] != "normal":
        print("[busy] LOI: menu Lich su bi khoa (chi doc, phai mo duoc)", flush=True)
        ok = False

    tb.set_busy(False)
    app.update()
    idle = {
        "convert": tb.convert_btn.cget("text"),
        "merge": tools.entrycget(tb._merge_index, "state"),
        "settings": tools.entrycget(tb._settings_index, "state"),
        "export": tb.export_btn.cget("state"),
    }
    print("[idle]", idle, flush=True)
    if "Chuyển đổi" not in idle["convert"] or idle["export"] != "normal" \
            or idle["merge"] != "normal" or idle["settings"] != "normal":
        print("[idle] LOI: trang thai sau khi ra khong khoi phuc", flush=True)
        ok = False

    # ── 5. Mở dialog Lịch sử từ menu ──
    tools.invoke(tb._history_index)
    app.update()
    toplevels = [w for w in app.winfo_children() if w.winfo_class() == "Toplevel"]
    print("[menu] invoke Lich su -> dialog:", len(toplevels), flush=True)
    if not toplevels:
        print("[menu] LOI: menu Lich su khong mo dialog", flush=True)
        ok = False
    for win in toplevels:
        win.destroy()
    app.update()

    app.destroy()
    print("\nKẾT QUẢ:", "OK" if ok else "LỖI", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
