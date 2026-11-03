"""Probe: thẻ cảm xúc/nghỉ + thanh chèn nhanh + lịch sử bản dựng.

Chạy: .venv\\Scripts\\python.exe packaging\\probe_tags_history.py
"""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from core.history import HistoryStore
from ui.main_window import MainWindow

TEXT = "Xin chào các bạn. [nghỉ 2s]. Chờ chút [nghỉ 3s] rồi đọc tiếp."


def wait_until(app, cond, timeout: float = 240.0) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        app.update()
        if cond():
            return True
        time.sleep(0.05)
    return False


def silence_runs(samples: np.ndarray, sr: int, min_sec: float = 1.0):
    """Danh sách (bắt đầu, độ dài) các đoạn im lặng >= min_sec."""
    quiet = np.abs(samples) < 1e-6
    runs: list[tuple[float, float]] = []
    start = None
    for i, flag in enumerate(quiet):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            if (i - start) / sr >= min_sec:
                runs.append((start / sr, (i - start) / sr))
            start = None
    if start is not None and (len(quiet) - start) / sr >= min_sec:
        runs.append((start / sr, (len(quiet) - start) / sr))
    return runs


def main() -> int:
    ok = True
    app = MainWindow()
    if getattr(app, "_prompt_job", None):
        app.after_cancel(app._prompt_job)
    app.geometry("1200x740")
    app.update_idletasks()
    app.update()
    print(f"[ui] header={app.topbar.winfo_height()}px tagbar={app.tag_bar.winfo_height()}px")

    # ── 1. Chèn thẻ qua thanh chèn nhanh ──
    app.textbox.set_text("")
    app.textbox.insert_at_cursor("[cười]")
    inserted = app.textbox.get_text()
    print(f"[tag] chèn tại con trỏ: {inserted!r}")
    ok &= "[cười]" in inserted

    # ── 2. Chuyển đổi văn bản có thẻ nghỉ ──
    app.textbox.set_text(TEXT)
    app._refresh_tag_hint()
    app.update()
    t0 = time.time()
    app._start_convert()
    done = wait_until(app, lambda: not app._busy and app._play_store is not None
                      and not app._speed_applying and not app._speed_dirty)
    print(f"[tts] chuyển đổi xong: {done} ({time.time() - t0:.1f}s)")
    ok &= done
    if not done:
        app.destroy()
        return 1

    app._player.stop()
    store = app._play_store
    sr = app._timeline.sample_rate
    total = store.total_samples
    samples = np.asarray(store.read(0, total), dtype=np.float32)
    print(f"[tts] tổng {total / sr:.2f}s / {len(app._timeline.sentences)} câu")
    runs = silence_runs(samples, sr, min_sec=1.8)
    print(f"[tts] khoảng lặng >=1.8s: {[(round(a, 2), round(d, 2)) for a, d in runs]}")
    # [nghỉ 2s] đứng riêng câu -> cộng thêm pad giữa câu (~0.3s)
    ok &= any(2.0 <= d <= 2.6 for _, d in runs)
    # [nghỉ 3s] giữa câu -> đúng 3s
    ok &= any(abs(d - 3.0) < 0.06 for _, d in runs)

    # ── 3. Xuất file -> ghi lịch sử ──
    out = Path(tempfile.gettempdir()) / "opencode" / "_probe_tags.mp3"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    app._set_busy(True)
    app._export_worker(str(out), app.topbar.get_speed(),
                       app.topbar.get_selected_voice())
    exported = wait_until(app, lambda: out.exists() and out.stat().st_size > 0, 90)
    app._set_busy(False)
    print(f"[export] {out.name}: {out.stat().st_size if out.exists() else 0} bytes")
    ok &= exported

    entries = app._history.entries
    print(f"[history] {len(entries)} bản ghi")
    if entries:
        entry = entries[0]
        audio_path = app._history.audio_path(entry)
        same_file = audio_path.resolve() == out.resolve()
        no_copy = not (app._history.root / entry.id).exists()
        print(f"[history] giọng={entry.voice!r} {entry.speed_text} "
              f"{entry.duration_text} {entry.size_text} "
              f"dung_file_goc={same_file} khong_ban_sao={no_copy}")
        ok &= same_file and no_copy
        ok &= audio_path.exists()
        ok &= entry.duration > 0
        removed = app._history.remove(entry.id)
        print(f"[history] xoá mục: {removed} còn {len(app._history.entries)} "
              f"file_goc_con={out.exists()}")
        ok &= removed and out.exists() and audio_path.exists()

    # ── 4. Trang lịch sử mở được ──
    app.shell.show("history")
    app.update()
    app.shell.show("text")
    app.update()
    print("[history] page mở/đóng OK")

    app.destroy()
    print("KẾT QUẢ:", "OK" if ok else "LỖI")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
