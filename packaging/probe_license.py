"""Probe P2: hộp thoại kích hoạt, badge bản quyền, các trạng thái chặn.

Chạy:  .venv\\Scripts\\python.exe packaging\\probe_license.py
Dùng thư mục tạm trong build/ nên KHÔNG đụng bản quyền thật của máy.
"""

from __future__ import annotations

import json
import shutil
import sys
import time
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.licensing import fingerprint, guard, shortcode, store, trial  # noqa: E402
from ui.components.activation_dialog import ActivationDialog  # noqa: E402
from ui.main_window import MainWindow  # noqa: E402

BASE = ROOT / "build" / "_probe_license"
ok = True


def check(name: str, condition: bool, detail: str = "") -> None:
    global ok
    print(f"[{'OK ' if condition else 'LOI'}] {name}" + (f" — {detail}" if detail else ""),
          flush=True)
    ok = ok and bool(condition)


def fresh(sub: str) -> Path:
    path = BASE / sub
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)
    store.configure(path, registry=False)
    guard.reset_cache()
    return path


def code(kind: int = shortcode.KIND_MONTH, m24: int | None = None,
         today: date | None = None) -> str:
    return shortcode.issue(fingerprint.machine24() if m24 is None else m24,
                           kind, today=today)


def dialog_for(app, timeout: float = 0.3) -> ActivationDialog:
    dialog = ActivationDialog(app)
    app.update()
    time.sleep(timeout)
    app.update()
    return dialog


def main() -> int:
    fresh("start")
    app = MainWindow()
    app.update()
    app._refresh_license_badge()
    check("chưa kích hoạt: badge cảnh báo",
          "Chưa kích hoạt" in app.topbar.license_label.cget("text"),
          app.topbar.license_label.cget("text"))

    # 1. Hộp thoại hiện mã máy 10 ký tự + có nút dùng thử
    dialog = dialog_for(app)
    check("dialog hiện mã máy 10 ký tự",
          dialog.machine_entry.get() == fingerprint.format_machine_code(),
          dialog.machine_entry.get())
    check("dialog có nút dùng thử", bool(dialog.trial_btn.winfo_manager()))
    dialog._on_close()

    # 2. Dùng thử 7 ngày
    trial.start()
    app._refresh_license_badge()
    check("dùng thử: badge đúng",
          "Dùng thử: còn 7 ngày" in app.topbar.license_label.cget("text"),
          app.topbar.license_label.cget("text"))

    # 3. Kích hoạt bằng mã đúng qua dialog
    fresh("activate")
    dialog = dialog_for(app)
    dialog.key_entry.insert(0, code())
    dialog._activate()
    check("kích hoạt: dialog trả kết quả", dialog.result is not None
          and dialog.result.active, str(dialog.result and dialog.result.state))
    check("kích hoạt: đã ghi license.json", store.license_path().exists())
    app._refresh_license_badge()
    check("kích hoạt: badge 30 ngày",
          "Còn 30 ngày" in app.topbar.license_label.cget("text"),
          app.topbar.license_label.cget("text"))

    # 4. Mã của máy khác
    fresh("other")
    dialog = dialog_for(app)
    dialog.key_entry.insert(0, code(m24=fingerprint.machine24() ^ 0x1))
    dialog._activate()
    check("máy khác: bị từ chối",
          dialog.result is None and "máy khác" in dialog.error_label.cget("text").lower(),
          dialog.error_label.cget("text"))
    check("máy khác: không ghi license", not store.license_path().exists())
    dialog._on_close()

    # 5. Sửa license.json
    fresh("tamper")
    guard.install(code(), now=time.time())
    data = json.loads(store.license_path().read_text(encoding="utf-8"))
    data["key"] = code(shortcode.KIND_WEEK)
    store.license_path().write_text(json.dumps(data), encoding="utf-8")
    guard.reset_cache()
    check("sửa JSON: bị phát hiện",
          guard.check_startup().state == guard.TAMPERED)

    # 6. Clone (CPU + mainboard đều khác)
    fresh("clone")
    now = time.time()
    fp = fingerprint.fp4()
    bad = dict(fp)
    bad["cpu"] ^= 0xFFFF
    bad["board"] ^= 0xFFFF
    store.save_license(fingerprint.machine_code(),
                       shortcode.format_code(code()), bad,
                       int(now), int(now))
    guard.reset_cache()
    check("clone: bị chặn",
          guard.check_startup(now).state == guard.CLONE_DETECTED)

    # 7. Lùi đồng hồ 4 ngày
    fresh("clock")
    now = time.time()
    guard.install(code(), now=now)
    guard.reset_cache()
    check("lùi 4 ngày: bị chặn",
          guard.check_startup(now - 4 * 86400).state == guard.CLOCK_ROLLBACK)
    guard.reset_cache()
    check("lùi 2 ngày: vẫn dùng được",
          guard.check_startup(now - 2 * 86400).state == guard.LICENSED)

    # 8. Nhập sai 11 lần -> khoá 60 giây
    fresh("ratelimit")
    now = time.time()
    for _ in range(store.LOCK_THRESHOLD):
        try:
            guard.install("AAAAA-AAAAA-AAAAA", now=now)
        except guard.LicenseError:
            pass
    dialog = dialog_for(app)
    dialog._refresh_lock()
    app.update()
    check("sai nhiều lần: nút kích hoạt bị khoá",
          str(dialog.activate_btn.cget("state")) == "disabled",
          str(dialog.activate_btn.cget("text")))
    dialog._on_close()

    # Trả về trạng thái thật của máy này
    store.configure(None, registry=True)
    guard.reset_cache()
    app._on_close()
    print("\nKẾT QUẢ:", "OK" if ok else "CÓ LỖI", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
