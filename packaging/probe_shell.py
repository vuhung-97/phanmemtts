"""Probe: shell SaaS (header / toolbar / sidebar / page / player).

Chạy: .venv\\Scripts\\python.exe packaging\\probe_shell.py
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

_TMP = Path(tempfile.mkdtemp(prefix="ppmitts_shell_"))
os.environ["LOCALAPPDATA"] = str(_TMP)

from core.licensing import store          # noqa: E402
from ui.main_window import MainWindow      # noqa: E402
from ui.shell.nav_sidebar import NAV_MAIN, NAV_TOOLS  # noqa: E402

SIZES = (("1280x800", 1280, 800), ("1024x700", 1024, 700),
         ("1440x900", 1440, 900))


def pump(app, seconds: float) -> None:
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
    pump(app, 0.8)
    shell = app.shell
    tb = shell.toolbar

    # ── 1. Kích thước ──
    print("[size] size | header | toolbar | sidebar | player | textbox")
    for label, w, h in SIZES:
        app.geometry(f"{w}x{h}")
        pump(app, 0.25)
        vals = (shell.header.winfo_height(), tb.winfo_height(),
                shell.sidebar.winfo_width(), shell.player_bar.winfo_height(),
                app.textbox.winfo_height())
        print(f"[size] {label} | {vals[0]} | {vals[1]} | {vals[2]} | "
              f"{vals[3]} | {vals[4]}", flush=True)
        if vals[0] != 56 or vals[1] != 40 or vals[2] != 232 or vals[3] != 108:
            print("[size] LOI: header/toolbar/sidebar/player sai kich thuoc")
            ok = False
        if vals[4] < 300:
            print(f"[size] LOI: khung soan thao qua thap ({vals[4]}px)")
            ok = False

    # ── 2. Toolbar / menu ──
    labels = {}
    for key, menu in tb.menus.items():
        items = []
        for i in range(menu.index("end") + 1):
            if menu.type(i) == "command":
                items.append(menu.entrycget(i, "label"))
        labels[key] = items
    print("[menu]", labels, flush=True)
    if list(labels) != ["file", "help"]:
        print("[menu] LOI: chi duoc co Tep / Tro giup")
        ok = False
    for want in ("Mở văn bản…", "Mở thư mục dữ liệu…", "Thoát"):
        if want not in labels.get("file", []):
            print(f"[menu] LOI: thieu {want}")
            ok = False
    for want in ("Hướng dẫn sử dụng", "Điều khoản sử dụng",
                 "Thông tin bản quyền", "Giới thiệu"):
        if want not in labels.get("help", []):
            print(f"[menu] LOI: thieu {want}")
            ok = False

    shortcuts = {"<Control-o>": "mo file", "<Control-Shift-L>": "ban quyen",
                 "<Alt-f>": "menu Tep", "<Alt-t>": "menu Tro giup",
                 "<Control-Key-1>": "page 1", "<Control-Key-2>": "page 2"}
    print("[key]", {k: bool(app.bind(k)) for k in shortcuts}, flush=True)
    for seq in shortcuts:
        if not app.bind(seq):
            print(f"[key] LOI: chua bind {seq}")
            ok = False

    # ── 3. Sidebar + điều hướng ──
    nav_ids = [x[0] for x in NAV_MAIN + NAV_TOOLS]
    print("[nav] items:", nav_ids, flush=True)
    if nav_ids != ["text", "dialogue", "merge", "batch", "history",
                   "dictionary", "voices", "settings", "license"]:
        print("[nav] LOI: danh sach muc sai")
        ok = False

    app.textbox.set_text("Nội dung kiểm tra giữ trạng thái.")
    app.update()
    app.shell.sidebar._navigate("dialogue")
    pump(app, 0.2)
    print("[nav] dialogue page:", shell.current_page.page_id, flush=True)
    if shell.current_page.page_id != "dialogue":
        print("[nav] LOI: khong chuyen sang page Hoi thoai")
        ok = False
    app.shell.sidebar._navigate("text")
    pump(app, 0.2)
    kept = app.textbox.get_text()
    print("[nav] quay lai text, giu noi dung:", kept.startswith("Nội dung"))
    if not kept.startswith("Nội dung"):
        print("[nav] LOI: mat noi dung khi chuyen page")
        ok = False

    # ── 4. Thu gọn sidebar ──
    shell.sidebar.toggle_collapsed()
    pump(app, 0.3)
    collapsed = shell.sidebar.winfo_width()
    shell.sidebar.toggle_collapsed()
    pump(app, 0.3)
    expanded = shell.sidebar.winfo_width()
    print(f"[nav] sidebar thu gon={collapsed} mo rong={expanded}", flush=True)
    if collapsed != 64 or expanded != 232:
        print("[nav] LOI: thu gon/mo rong sai")
        ok = False

    # ── 5. Busy: khoá menu + tab + nút ──
    app._set_busy(True)
    pump(app, 0.2)
    state = {
        "convert": app.text_page.convert_btn.cget("text"),
        "export": app.text_page.export_btn.cget("state"),
        "file_menu": tb._menu_buttons["file"].cget("state"),
    }
    shell.sidebar._navigate("dialogue")
    pump(app, 0.2)
    stayed = shell.current_page.page_id
    print("[busy]", state, "| page sau khi bam:", stayed, flush=True)
    if "Dừng" not in state["convert"] or state["export"] != "disabled":
        print("[busy] LOI: nut chinh khong doi Dung / khoa xuat")
        ok = False
    if state["file_menu"] != "disabled":
        print("[busy] LOI: menu Tep khong bi khoa")
        ok = False
    if stayed != "text":
        print("[busy] LOI: van chuyen duoc page khi dang ban")
        ok = False

    app._set_busy(False)
    pump(app, 0.2)
    idle = {
        "convert": app.text_page.convert_btn.cget("text"),
        "export": app.text_page.export_btn.cget("state"),
        "file_menu": tb._menu_buttons["file"].cget("state"),
    }
    print("[idle]", idle, flush=True)
    if "Chuyển đổi" not in idle["convert"] or idle["export"] != "normal" \
            or idle["file_menu"] != "normal":
        print("[idle] LOI: khong khoi phuc trang thai")
        ok = False

    # ── 6. Player / status ──
    speed = shell.player_bar.get_speed()
    print("[player] speed:", speed, "| time:", shell.player_bar.time_label.cget("text"),
          flush=True)
    if abs(speed - 1.0) > 1e-9:
        print("[player] LOI: toc do mac dinh khac 1.0")
        ok = False
    shell.status("Kiểm tra trạng thái", "#2563EB")
    app.update()
    if tb.status_label.cget("text") != "Kiểm tra trạng thái":
        print("[status] LOI: khong cap nhat thanh trang thai")
        ok = False

    # ── 7. Player luôn hiển thị ──
    mapped = shell.player_bar.winfo_ismapped()
    disabled = str(shell.player_bar.toggle_btn.cget("state"))
    shell.player_bar.set_transport_enabled(True)
    app.update()
    enabled = str(shell.player_bar.toggle_btn.cget("state"))
    shell.player_bar.set_transport_enabled(False)
    app.update()
    print("[player] luon hien:", bool(mapped), "| rong thi disable:", disabled,
          "| co audio thi enable:", enabled)
    if not mapped or disabled != "disabled" or enabled != "normal":
        print("[player] LOI: trang thai player sai")
        ok = False

    app.destroy()
    print("\nKẾT QUẢ:", "OK" if ok else "LỖI", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
