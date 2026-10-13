"""Tạo file giọng di động (.json) từ file mẫu âm thanh.

Chạy trên MÁY KHỎE (cần nạp model ~7s + enroll ~3s):

    python tools/tao_giong.py --ten "Giọng A" --mau ref.wav --ra "Giọng A.json"

Sao đó: copy file .json sang MÁY YẾU ->
app -> Quản lý giọng đọc -> ＋ Thêm giọng mới -> chọn file -> Nhập.

Mẫu lý tưởng: 5-30 giây, 1 người nói rõ, ít tiếng ồn/nhạc (wav/mp3/flac).
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Console Windows hay là cp125x -> tiếng Việt/emoji bị lỗi khi in.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Tạo file giọng VieNeu (.json) từ file mẫu âm thanh.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--ten", required=True, help="Tên giọng (vd: Giọng A)")
    ap.add_argument("--mau", required=True,
                    help="File mẫu âm thanh (wav/mp3/flac, 5-30 giây)")
    ap.add_argument("--ra", default=None,
                    help="File output .json (mặc định: <ten>.json)")
    ap.add_argument("--mota", default="", help="Mô tả giọng (tùy chọn)")
    ap.add_argument("--khong-khui-noise", action="store_true",
                    help="Bỏ qua bước khử nhiễu (mẫu đã sạch rồi)")
    args = ap.parse_args()

    mau = Path(args.mau)
    if not mau.exists():
        print(f"[LOI] Khong tim thay file mau: {mau}")
        return 1
    out = Path(args.ra) if args.ra else Path(f"{args.ten}.json")

    try:
        print("[..] Dang nạp model VieNeu (lan dau ~7s)...")
        t0 = time.time()
        from engine.vieneu_engine import VieneuTTS
        tts = VieneuTTS()
        print(f"[OK] Model san sang ({time.time() - t0:.1f}s)")

        print("[..] Dang tao giong (trim + khui nhieu + speaker embedding)...")
        t1 = time.time()
        tts.create_voice_from_sample(
            args.ten, mau, description=args.mota,
            denoise=not args.khong_khui_noise,
        )
        print(f"[OK] Tao giong '{args.ten}' xong ({time.time() - t1:.1f}s)")

        tts.export_voice_file(args.ten, out)
        size_kb = max(out.stat().st_size // 1024, 1)
        print(f"[OK] File giong: {out.resolve()} ({size_kb} KB)")
        print("[OK] Da luu vao models/vieneu/custom_voices.json (may nay dung duoc luon).")
        print()
        print(f"==> Copy file '{out.name}' sang may yeu, roi trong app:")
        print("    Quan ly giong doc -> ＋ Them giong moi -> chon file -> Nhap")
        return 0
    except Exception as exc:
        print(f"[LOI] {exc}")
        if "speaker_encoder" in str(exc) or "Hub" in str(exc) or "connection" in str(exc):
            print("[GOI Y] Lan dau tao giong can mang de tai speaker_encoder.onnx "
                  "(26MB): chay 'python download_model.py' roi chay lai lenh nay.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
