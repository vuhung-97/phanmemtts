"""Probe: chuyển đổi hàng loạt [P1]/[P2] -> nhiều tệp + .zip (model thật).

Chạy: .venv\\Scripts\\python.exe packaging\\probe_batch.py
Dùng thư mục tạm trong build/ nên không đụng dữ liệu thật.
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_TMP = Path(tempfile.mkdtemp(prefix="ppmitts_batch_"))
os.environ["LOCALAPPDATA"] = str(_TMP)

from core.licensing import fingerprint, guard, shortcode, store  # noqa: E402
from ui.main_window import MainWindow          # noqa: E402

TEXT = """Lời dẫn đầu chương trình.
[P1] Xin chào, đây là phần một.
[P2] Tạm biệt, đây là phần hai.
"""


def activate() -> None:
    """Kích hoạt vĩnh viễn trong thư mục tạm để probe được xuất file."""
    store.configure(_TMP / "license", registry=False)
    guard.reset_cache()
    code = shortcode.issue(fingerprint.machine24(), shortcode.KIND_LIFETIME)
    guard.install(code, now=time.time())


def pump(app, seconds: float) -> None:
    end = time.time() + seconds
    while time.time() < end:
        app.update()
        time.sleep(0.02)


def main() -> int:
    ok = True
    activate()
    app = MainWindow()
    if getattr(app, "_prompt_job", None):
        app.after_cancel(app._prompt_job)
    if getattr(app, "_prompt_job", None):
        app.after_cancel(app._prompt_job)
    app.geometry("1200x740")
    pump(app, 1.0)

    model = app._selected_model()
    if model is None:
        print("LOI: khong co model giong doc", flush=True)
        return 1

    app.shell.show("batch")
    out_dir = _TMP / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    pump(app, 0.3)
    dialog = app.batch_page
    print("[button] xuat:", dialog.start_btn.cget("text"))
    if "💾" not in dialog.start_btn.cget("text"):
        print("[button] LOI: nut xuat thieu icon")
        ok = False
    dialog.editor.delete("1.0", "end")
    dialog.editor.insert("1.0", TEXT)
    dialog._parse()

    parts = dialog._parts
    labels = [p.label for p in parts]
    print("[parse] phan:", labels, flush=True)
    if labels != ["P0", "P1", "P2"]:
        print("[parse] LOI: tach phan sai", flush=True)
        ok = False

    dialog.base_entry.delete(0, "end")
    dialog.base_entry.insert(0, "bai")
    dialog.folder_entry.delete(0, "end")
    dialog.folder_entry.insert(0, str(out_dir))
    dialog.zip_var.set(True)
    dialog.format_var.set("mp3")
    dialog._start()

    deadline = time.time() + 180
    while dialog._running and time.time() < deadline:
        app.update()
        time.sleep(0.05)
    pump(app, 0.5)

    files = sorted(p.name for p in out_dir.glob("*.mp3"))
    archive = sorted(p.name for p in out_dir.glob("*.zip"))
    print("[out] files:", files, "| zip:", archive, flush=True)
    expected = ["bai_P0.mp3", "bai_P1.mp3", "bai_P2.mp3"]
    if files != expected:
        print(f"[out] LOI: mong doi {expected}", flush=True)
        ok = False
    if archive != ["bai.zip"]:
        print("[out] LOI: thieu tep zip", flush=True)
        ok = False
    sizes = {p.name: p.stat().st_size for p in out_dir.glob("*.mp3")}
    print("[out] dung luong:", sizes, flush=True)
    if any(size < 1000 for size in sizes.values()):
        print("[out] LOI: tep audio qua nho", flush=True)
        ok = False

    print("[history] so ban:", len(app._history.entries))
    if len(app._history.entries) < 3:
        print("[history] LOI: hang loat khong ghi lich su")
        ok = False

    status = dialog.status_label.cget("text")
    print("[status]", status, flush=True)
    if "Xong" not in status:
        print("[status] LOI: khong bao xong", flush=True)
        ok = False

    app.shell.show("text")
    app.update()
    app.destroy()
    print("\nKẾT QUẢ:", "OK" if ok else "LỖI", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
