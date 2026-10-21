"""Probe P0 (UI): chạy thật luồng chuyển đổi trong MainWindow.

Kiểm tra: đệm text -> Chuyển đổi -> streaming -> xuất file -> đổi tốc độ,
ở cả chế độ RAM và chế độ đĩa (bài dài).

Chạy: .venv\\Scripts\\python.exe packaging\\probe_ui_flow.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from ui.main_window import MainWindow

TEXT = ("Xin chào, đây là bài kiểm tra luồng chuyển đổi sau khi đổi kiến trúc bộ nhớ. "
        "Câu thứ hai nói về việc đọc file và xuất âm thanh. "
        "Câu thứ ba để kiểm tra việc tạo audio theo từng câu.")


def ram_mb() -> float:
    """Working set hiện tại của tiến trình (MB) — dùng ctypes cho Windows."""
    import ctypes
    from ctypes import wintypes

    class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    counters = PROCESS_MEMORY_COUNTERS()
    counters.cb = ctypes.sizeof(counters)
    handle = ctypes.windll.kernel32.GetCurrentProcess()
    try:
        psapi = ctypes.WinDLL("psapi")
    except OSError:
        psapi = ctypes.WinDLL("kernel32")
    fn = psapi.GetProcessMemoryInfo
    fn.argtypes = [ctypes.c_void_p, ctypes.POINTER(PROCESS_MEMORY_COUNTERS),
                   ctypes.c_ulong]
    fn.restype = ctypes.c_int
    ok = fn(ctypes.c_void_p(handle), ctypes.byref(counters), counters.cb)
    if not ok:
        return 0.0
    return counters.WorkingSetSize / (1024 * 1024)


def pump(app: MainWindow, seconds: float) -> None:
    """Chạy vòng lặp Tk trong khoảng thời gian cho trước."""
    end = time.time() + seconds
    while time.time() < end:
        app.update()
        time.sleep(0.02)


def wait_status(app: MainWindow, needle: str, timeout: float = 300.0) -> bool:
    end = time.time() + timeout
    last_log = 0.0
    while time.time() < end:
        app.update()
        try:
            text = app.topbar.status_label.cget("text")
        except Exception:
            text = ""
        if needle.lower() in str(text).lower():
            return True
        now = time.time()
        if now - last_log >= 10:
            last_log = now
            n = len(app._timeline.sentences) if app._timeline else 0
            print(f"    ... [{int(now % 10000)}] '{text}' | cau={n} | "
                  f"busy={app._busy}", flush=True)
        time.sleep(0.05)
    return False


def run_case(app: MainWindow, storage: str, text: str, label: str) -> bool:
    print(f"\n=== {label} (storage={storage}) ===", flush=True)
    app._settings["storage"] = storage
    app.textbox.set_text(text)
    app.topbar.speed_combo.set("1.0x")
    t0 = time.time()
    app._start_convert()
    print("[ui] da bat dau chuyen doi...", flush=True)
    ok = wait_status(app, "Hoàn tất", timeout=900)
    print(f"[ui] chuyen doi xong: {ok} ({time.time() - t0:.1f}s)", flush=True)
    if not ok:
        print("[ui] status:", app.topbar.status_label.cget("text"))
        return False
    print(f"[ui] cau: {len(app._timeline.sentences)} | "
          f"thoi luong: {app._timeline.total_duration:.2f}s | "
          f"mau play: {app._play_store.total_samples} | "
          f"RAM: {ram_mb():.0f} MB | che do dia: {app._disk_mode}", flush=True)
    if app._play_store.total_samples <= 0:
        print("[ui] LOI: khong co audio", flush=True)
        return False

    # Xuất file
    out = ROOT / "build" / f"_probe_ui_{storage}.mp3"
    out.parent.mkdir(parents=True, exist_ok=True)
    import audio.exporter as exporter

    exporter.export_source(app._play_store, app._sample_rate, out)
    size = out.stat().st_size
    print(f"[ui] xuat file: {out.name} ({size} bytes)", flush=True)
    if size <= 0:
        print("[ui] LOI: file rong", flush=True)
        return False

    # Đổi tốc độ -> dựng lại audio
    app.topbar.set_status("")   # xoá status cũ để không match nhầm
    app.topbar.speed_combo.set("1.5x")
    app._on_speed_change(1.5)
    pump(app, 0.3)
    print("[ui] dang doi toc do 1.0x -> 1.5x ...", flush=True)
    app._request_speed_apply(auto_play=False)
    t1 = time.time()
    ok2 = wait_status(app, "Đã áp tốc độ", timeout=600)
    print(f"[ui] doi toc do: {ok2} ({time.time() - t1:.1f}s) | "
          f"thoi luong moi: {app._timeline.total_duration:.2f}s | "
          f"RAM: {ram_mb():.0f} MB", flush=True)
    if not ok2:
        print("[ui] status:", app.topbar.status_label.cget("text"), flush=True)
        return False

    exporter.export_source(app._play_store, app._sample_rate,
                           ROOT / "build" / f"_probe_ui_{storage}_x15.mp3")
    out.unlink(missing_ok=True)
    (ROOT / "build" / f"_probe_ui_{storage}_x15.mp3").unlink(missing_ok=True)
    return True


def main() -> int:
    app = MainWindow()
    pump(app, 0.5)

    ok1 = run_case(app, "memory", TEXT, "Bai ngan (RAM)")
    ok2 = run_case(app, "disk", TEXT, "Bai ngan (dia)")

    # Bài dài: ép chế độ đĩa + văn bản lớn -> kiểm tra không nổ RAM
    long_text = (TEXT + " ") * 12
    ok3 = run_case(app, "disk", long_text, "Bai dai (dia)")

    app._on_close()
    print("\n[ui] KET QUA:",
          "OK" if (ok1 and ok2 and ok3) else "CO LOI", flush=True)
    return 0 if (ok1 and ok2 and ok3) else 1


if __name__ == "__main__":
    raise SystemExit(main())
