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

from core.licensing import edition, store   # noqa: E402
from ui.main_window import MainWindow      # noqa: E402
from ui.shell.nav_sidebar import nav_items  # noqa: E402

SIZES = (("1280x800", 1280, 800), ("1024x700", 1024, 700),
         ("1024x640", 1024, 640), ("1440x900", 1440, 900))


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
        min_editor = 300 if h >= 700 else 220
        if vals[4] < min_editor:
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
    want_help = ["Hướng dẫn sử dụng", "Điều khoản sử dụng"]
    if edition.license_visible():
        want_help.append("Thông tin bản quyền")
    want_help.append("Giới thiệu")
    for want in want_help:
        if want not in labels.get("help", []):
            print(f"[menu] LOI: thieu {want}")
            ok = False
    if not edition.license_visible() and "Thông tin bản quyền" in labels.get("help", []):
        print("[menu] LOI: ban full van hien muc Ban quyen")
        ok = False

    shortcuts = {"<Control-o>": "mo file",
                 "<Alt-f>": "menu Tep", "<Alt-t>": "menu Tro giup",
                 "<Control-Key-1>": "page 1", "<Control-Key-2>": "page 2"}
    if edition.license_visible():
        shortcuts["<Control-Shift-L>"] = "ban quyen"
    print("[key]", {k: bool(app.bind(k)) for k in shortcuts}, flush=True)
    for seq in shortcuts:
        if not app.bind(seq):
            print(f"[key] LOI: chua bind {seq}")
            ok = False

    # ── 2b. Widget trong toolbar phải nằm gọn trong 40 px ──
    clipped = []
    for child in tb.winfo_children():
        if not child.winfo_ismapped():
            continue
        if child.winfo_y() < 0 or child.winfo_y() + child.winfo_height() > tb.winfo_height() + 1:
            clipped.append((child.__class__.__name__, child.winfo_y(),
                            child.winfo_height()))
    print("[toolbar] widget bi cat:", clipped)
    if clipped:
        print("[toolbar] LOI: noi dung toolbar tran ra ngoai")
        ok = False
    menu_clipped = [w for w in tb._menu_buttons.values()
                    if not w.winfo_ismapped() or w.winfo_height() < 20]
    if menu_clipped:
        print("[toolbar] LOI: nut menu khong hien")
        ok = False

    # ── 3. Sidebar + điều hướng ──
    nav_ids = [x[0] for x in nav_items()]
    print("[nav] items:", nav_ids, flush=True)
    expected_nav = ["text", "dialogue", "merge", "batch", "history",
                    "dictionary", "voices", "settings"]
    if edition.license_visible():
        expected_nav.append("license")
    if nav_ids != expected_nav:
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

    # ── 8. Scroll dự phòng khi cửa sổ nhỏ ──
    from ui.ui_kit import ScrollArea

    app.geometry("1024x640")
    pump(app, 0.4)
    for pid in nav_ids:
        shell.show(pid)
        pump(app, 0.15)
        page = shell.current_page
        if not isinstance(page.body, ScrollArea):
            print(f"[scroll] LOI: {pid} khong co ScrollArea")
            ok = False
    for pid, want in (("settings", True), ("license", True),
                      ("text", False), ("dictionary", False),
                      ("merge", False)):
        shell.show(pid)
        pump(app, 0.3)
        page = shell.current_page
        bar = page.body.scrollbar_visible
        print(f"[scroll] {pid} @1024x640 thanh cuon: {bar}", flush=True)
        if bar is not want:
            print(f"[scroll] LOI: {pid} sai trang thai thanh cuon")
            ok = False
        if bar:
            page.body.scroll_to_bottom()
            pump(app, 0.15)
            canvas = page.body._parent_canvas
            last = page.body.winfo_children()[-1]
            visible = (last.winfo_rooty() + last.winfo_height()
                       <= canvas.winfo_rooty() + canvas.winfo_height() + 2)
            print(f"[scroll] {pid} cuon toi cuoi, thay card cuoi: {visible}")
            if not visible:
                print(f"[scroll] LOI: {pid} khong cuon toi cuoi duoc")
                ok = False
            page.body.scroll_to_top()

    app.geometry("1280x800")
    pump(app, 0.4)
    for pid in ("settings", "license"):
        shell.show(pid)
        pump(app, 0.3)
        bar = shell.current_page.body.scrollbar_visible
        print(f"[scroll] {pid} @1280x800 thanh cuon: {bar}", flush=True)
        if bar:
            print(f"[scroll] LOI: {pid} van hien thanh cuon khi du cho")
            ok = False

    app.destroy()
    print("\nKẾT QUẢ:", "OK" if ok else "LỖI", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
