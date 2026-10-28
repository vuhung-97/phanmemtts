"""Probe: điều khoản sử dụng lần đầu + cam kết khi tạo giọng.

1. Lần chạy đầu: `_terms_accepted()` = False.
2. Hộp thoại: nút "Đồng ý" bị khoá cho tới khi tick.
3. Tick + đồng ý -> ghi `app_settings.json` (terms_version, terms_accepted_at)
   và `_terms_accepted()` = True.
4. Tab tạo giọng có checkbox cam kết; không tick -> không cho tạo.
5. Menu Trợ giúp có mục "Điều khoản sử dụng".

Chạy: .venv\\Scripts\\python.exe packaging\\probe_terms.py
"""

from __future__ import annotations

import json
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

_TMP = Path(tempfile.mkdtemp(prefix="ppmitts_terms_"))
os.environ["LOCALAPPDATA"] = str(_TMP)

from core.licensing import store                      # noqa: E402
from ui.components.terms_dialog import (              # noqa: E402
    TERMS_VERSION, TermsDialog, terms_text)
from ui.main_window import MainWindow                 # noqa: E402


def pump(app, seconds: float) -> None:
    end = time.time() + seconds
    while time.time() < end:
        app.update()
        time.sleep(0.02)


def accept_open_dialog(app) -> bool:
    for widget in app.winfo_children():
        if widget.winfo_class() != "Toplevel":
            continue
        if not hasattr(widget, "accept_var"):
            continue
        widget.accept_var.set(True)
        widget._sync_accept_button()
        widget._accept()
        return True
    return False


def main() -> int:
    ok = True
    store.configure(_TMP / "license", registry=False)
    app = MainWindow()
    if getattr(app, "_prompt_job", None):
        app.after_cancel(app._prompt_job)
    pump(app, 0.6)

    # 1. Chưa đồng ý
    print("[terms] da dong y truoc khi chay:", app._terms_accepted(), flush=True)
    if app._terms_accepted():
        print("[terms] LOI: coi nhu da dong y khi chua co cau hinh", flush=True)
        ok = False

    text = terms_text()
    print("[terms] tep dieu khoan:", len(text), "ky tu", flush=True)
    if len(text) < 500 or "offline" not in text.lower():
        print("[terms] LOI: noi dung dieu khoan qua ngan / thieu", flush=True)
        ok = False

    # 2. Nút đồng ý khoá khi chưa tick
    dialog = TermsDialog(app, require_accept=True)
    app.update()
    state_before = str(dialog.accept_btn.cget("state"))
    dialog.accept_var.set(True)
    dialog._sync_accept_button()
    state_after = str(dialog.accept_btn.cget("state"))
    print(f"[dialog] truoc tick={state_before} | sau tick={state_after}", flush=True)
    if state_before != "disabled" or state_after != "normal":
        print("[dialog] LOI: nut dong y khong khoa/mo dung", flush=True)
        ok = False
    dialog._decline()
    app.update()

    # 3. Luồng thật: _ask_terms (tự tick hộp thoại sau 250ms)
    app.after(250, lambda: accept_open_dialog(app))
    agreed = app._ask_terms()
    pump(app, 0.3)
    settings_path = _TMP / "PhanMemTTS" / "app_settings.json"
    saved = json.loads(settings_path.read_text(encoding="utf-8")) \
        if settings_path.exists() else {}
    print("[save] terms_version:", saved.get("terms_version"),
          "| accepted_at > 0:", float(saved.get("terms_accepted_at") or 0) > 0,
          flush=True)
    if not agreed or not app._terms_accepted():
        print("[save] LOI: khong ghi nhan dong y", flush=True)
        ok = False
    if saved.get("terms_version") != TERMS_VERSION:
        print("[save] LOI: sai phien ban dieu khoan", flush=True)
        ok = False

    # 4. Cam kết khi tạo giọng
    from ui.components.voice_import_dialog import ImportVoiceDialog

    created: list[str] = []
    import_dialog = ImportVoiceDialog(app, on_import=lambda _p: False,
                                      on_created=lambda n: created.append(n) or False)
    app.update()
    import_dialog._select_tab("create")
    app.update()
    import_dialog.create_name_entry.insert(0, "GiongProbe")
    import_dialog._sample_path = str(_TMP / "mau.wav")
    import_dialog._start_create()
    app.update()
    blocked = "cam kết" in import_dialog.create_status.cget("text").lower()
    print("[voice] chan khi chua cam ket:", blocked, flush=True)
    if not blocked or import_dialog._creating:
        print("[voice] LOI: khong chan tao giong khi chua cam ket", flush=True)
        ok = False
    import_dialog.commit_var.set(True)
    import_dialog._close()
    app.update()

    # 5. Menu Trợ giúp
    help_menu = app.topbar.menus["help"]
    labels = [help_menu.entrycget(i, "label")
              for i in range(help_menu.index("end") + 1)
              if help_menu.type(i) == "command"]
    print("[menu] Tro giup:", labels, flush=True)
    if "Điều khoản sử dụng" not in labels:
        print("[menu] LOI: thieu muc Dieu khoan", flush=True)
        ok = False

    app.destroy()
    print("\nKẾT QUẢ:", "OK" if ok else "LỖI", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
