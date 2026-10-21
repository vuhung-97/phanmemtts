"""Probe P0: kiểm tra lõi TTS + luồng store mới (RAM & đĩa) sau khi đổi kiến trúc.

Chạy: .venv\\Scripts\\python.exe packaging\\probe_p0.py
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

import numpy as np

from audio.buffer import GrowableBuffer
from audio.peaks import compute_peaks
from audio.temp_store import TempSession
from core.models import TimelineMap
from engine.model_manager import ModelManager
from engine.tts_engine import TtsEngine

TEXT = "Xin chào, đây là bản kiểm tra sau khi đổi kiến trúc bộ nhớ. Câu hai ở đây."


def main() -> int:
    t0 = time.time()
    mm = ModelManager()
    models = mm.scan()
    print(f"[probe] so giong: {len(models)}")
    if not models:
        print("[probe] LOI: khong tim thay model")
        return 2
    model = models[4] if len(models) > 4 else models[0]
    print(f"[probe] chon giong: {model.display_name}")

    tts = mm.load_tts(model)
    engine = TtsEngine(tts)
    print(f"[probe] model nap xong sau {time.time() - t0:.1f}s, sr={engine.sample_rate}")

    # ── 1. Tổng hợp như app (stream từng câu) ──
    pieces = []
    sentences = []
    for timed, piece, cur, tot in engine.synthesize_stream(TEXT, speed=1.0):
        pieces.append(piece)
        sentences.append(timed)
        print(f"[probe]   cau {cur}/{tot}: {len(piece)} mau")
    total_samples = sum(len(p) for p in pieces)
    print(f"[probe] tong hop: {len(pieces)} cau, {total_samples} mau "
          f"({total_samples / engine.sample_rate:.2f}s)")
    if total_samples == 0:
        print("[probe] LOI: khong co audio")
        return 3

    # ── 2. Store RAM ──
    buf = GrowableBuffer()
    for p in pieces:
        buf.append(p)
    assert buf.total_samples == total_samples
    raw_peak = float(np.max(np.abs(buf.view())))
    print(f"[probe] store RAM: {buf.total_samples} mau, peak goc = {raw_peak:.4f}")
    # PCM16 gioi han [-1, 1] -> so sanh tren du lieu da clip
    clipped = np.clip(buf.view(), -1.0, 1.0)
    peaks = compute_peaks(clipped, 300)
    print(f"[probe]   peaks: {peaks.size} cot, max={peaks.max():.3f}")
    assert peaks.size > 0 and peaks.max() > 0

    # ── 3. Store đĩa ──
    session = TempSession(ROOT / "build" / "_probe_tmp")
    disk = session.store("base", engine.sample_rate)
    for p in pieces:
        disk.append(p)
    out = disk.read(0, disk.total_samples)
    print(f"[probe] store dia: {disk.total_samples} mau -> doc lai "
          f"{out.size} mau")
    assert out.size == total_samples
    # PCM16 nén trong [-1, 1] -> so sánh với dữ liệu đã clip
    assert np.allclose(out, np.clip(buf.view(), -1.0, 1.0), atol=1e-3)
    peaks_disk = compute_peaks(disk, 300)
    print(f"[probe] peaks tren dia: max={peaks_disk.max():.3f}")
    assert np.allclose(peaks_disk, peaks, atol=1e-3)

    # ── 4. Xuất file từ source ──
    from audio import exporter
    out_path = ROOT / "build" / "_probe_out.wav"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    exporter.export_source(disk, engine.sample_rate, out_path)
    print(f"[probe] xuat wav: {out_path.stat().st_size} bytes")

    # ── 5. Timeline ──
    tl = TimelineMap(sentences=sentences, sample_rate=engine.sample_rate)
    scaled = tl.scaled(1.5)
    print(f"[probe] timeline: {tl.total_duration:.2f}s -> x1.5 = "
          f"{scaled.total_duration:.2f}s")
    assert scaled.total_duration < tl.total_duration

    disk.cleanup()
    session.cleanup()
    out_path.unlink(missing_ok=True)
    print(f"[probe] OK ({time.time() - t0:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
