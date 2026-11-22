"""Probe chống tăng RAM: đo Working Set trước/sau các thao tác thực tế.

Chạy nhanh (không cần model):
    .venv\\Scripts\\python.exe packaging\\probe_ram.py

Chạy kèm model (nạp ~13s, tổng hợp vài câu, đổi giọng):
    .venv\\Scripts\\python.exe packaging\\probe_ram.py --model

Mục tiêu:
- Đổi giọng KHÔNG nạp lại model, KHÔNG tăng RAM.
- Player/store giải phóng được audio.
- compute_peaks không quét toàn bộ audio.
- Undo có giới hạn -> RAM soạn thảo không tăng mãi.
"""

from __future__ import annotations

import ctypes
import gc
import sys
import time
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


class _ProcessMemoryCounters(ctypes.Structure):
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


def ram_mb() -> float:
    counters = _ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    handle = ctypes.windll.kernel32.GetCurrentProcess()
    try:
        psapi = ctypes.WinDLL("psapi")
    except OSError:
        psapi = ctypes.WinDLL("kernel32")
    fn = psapi.GetProcessMemoryInfo
    fn.argtypes = [ctypes.c_void_p, ctypes.POINTER(_ProcessMemoryCounters),
                   ctypes.c_ulong]
    fn.restype = ctypes.c_int
    if not fn(ctypes.c_void_p(handle), ctypes.byref(counters), counters.cb):
        return 0.0
    return counters.WorkingSetSize / (1024 * 1024)


def log(tag: str, before: float | None = None) -> float:
    gc.collect()
    now = ram_mb()
    delta = "" if before is None else f" (Δ {now - before:+.0f} MB)"
    print(f"{tag:48s} RAM={now:8.1f} MB{delta}", flush=True)
    return now


# ── Kiểm tra nhanh, không cần model ──

class _CountingSource:
    def __init__(self, total: int) -> None:
        self.total_samples = total
        self.samples_read = 0

    def read(self, start: int, n: int):
        import numpy as np

        n = max(0, min(int(n), self.total_samples - int(start)))
        self.samples_read += n
        return np.ones(n, dtype=np.float32)


def check_peaks() -> bool:
    from audio.peaks import compute_peaks

    source = _CountingSource(10_000_000)
    peaks = compute_peaks(source, 300)
    ok = (len(peaks) == 300 and source.samples_read <= 300 * 2048)
    print(f"[peaks] đọc {source.samples_read:,} mẫu / 10.000.000 -> "
          f"{'OK' if ok else 'LỖI'}", flush=True)
    return ok


def check_store_release() -> bool:
    import numpy as np

    from audio.buffer import GrowableBuffer
    from audio.player import AudioPlayer

    before = log("[release] trước khi tạo audio 80 MB")
    buf = GrowableBuffer()
    buf.append(np.ones(20_000_000, dtype=np.float32))
    player = AudioPlayer()
    player._available = False
    player.load_source(buf, 48000)
    peak = log("[release] sau khi tạo 80 MB + player")

    player.release_source()
    buf.cleanup()
    after = log("[release] sau release_source + cleanup")

    ok = after < peak - 50
    print(f"[release] giải phóng {'OK' if ok else 'LỖI'}", flush=True)
    return ok


def check_undo() -> bool:
    try:
        import customtkinter as ctk

        from ui.components.sync_textbox import SyncTextbox
    except Exception as exc:
        print(f"[undo] bỏ qua (không tạo được Tk): {exc}", flush=True)
        return True

    try:
        root = ctk.CTk()
        root.withdraw()
        root.update()
    except Exception as exc:
        print(f"[undo] bỏ qua (không có display): {exc}", flush=True)
        return True

    tb = SyncTextbox(root, on_text_changed=lambda: None)
    tb.pack()
    tb.set_text("".join("Dòng văn bản số %d để kiểm tra bộ nhớ.\n" % i
                        for i in range(1500)))
    root.update()
    start = log("[undo] sau khi nạp ~60k ký tự")
    inner = tb._textbox
    for i in range(3000):
        inner.insert("insert", "x")
        inner.delete("insert-1c")
        if (i + 1) % 1000 == 0:
            root.update()
    end = log("[undo] sau 3.000 thao tác sửa", start)
    tb.destroy()
    root.destroy()

    ok = end - start < 20
    print(f"[undo] maxundo có giới hạn {'OK' if ok else 'LỖI'}", flush=True)
    return ok


# ── Kiểm tra với model thật ──

def check_model() -> bool:
    from engine.model_manager import ModelManager

    mm = ModelManager()
    models = mm.scan()
    if len(models) < 2:
        print("[model] cần ít nhất 2 giọng để kiểm tra", flush=True)
        return False
    print(f"[model] low_memory={mm.low_memory()} | {len(models)} giọng",
          flush=True)

    t = time.time()
    tts_a = mm.load_tts(models[0])
    print(f"[model] nạp {models[0].model_id}: {time.time() - t:.1f}s",
          flush=True)
    after_load = log("[model] sau khi nạp")

    texts = [
        "Xin chào các bạn.",
        "Hôm nay trời đẹp và mát mẻ.",
        "Đây là câu dài hơn một chút để kiểm tra bộ nhớ khi tổng hợp "
        "nhiều câu liên tiếp trong cùng một phiên làm việc.",
    ]
    times = []
    for i in range(6):
        t = time.time()
        audio = tts_a.generate(texts[i % 3])
        times.append(time.time() - t)
        del audio
    after_infer = log("[model] sau 6 câu", after_load)

    t = time.time()
    tts_b = mm.load_tts(models[1])
    switch_ms = (time.time() - t) * 1000
    after_switch = log("[model] sau khi đổi giọng", after_infer)

    print(f"[model] đổi giọng: {switch_ms:.0f} ms | "
          f"cùng object={tts_b is tts_a}", flush=True)
    print(f"[model] thời gian 6 câu: "
          f"{', '.join(f'{x:.1f}s' for x in times)}", flush=True)

    ok = (tts_b is tts_a and switch_ms < 500 and after_switch - after_infer < 50)
    mm.unload()
    log("[model] sau unload")
    print(f"[model] đổi giọng không nạp lại {'OK' if ok else 'LỖI'}", flush=True)
    return ok


def main(argv: list[str]) -> int:
    print("=== Probe chống tăng RAM ===", flush=True)
    results = [check_peaks(), check_store_release(), check_undo()]
    if "--model" in argv:
        results.append(check_model())
    ok = all(results)
    print("\nKẾT QUẢ:", "OK" if ok else "CÓ LỖI", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
