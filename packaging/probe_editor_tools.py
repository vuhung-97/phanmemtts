"""Probe: công cụ soạn thảo (làm sạch + từ điển phát âm).

Kiểm tra trên app thật (cửa sổ ẩn):
1. Nút 📖 Từ điển / 🧹 Làm sạch có trên thanh chèn nhanh + menu Công cụ.
2. Làm sạch: bỏ dòng trống thừa, gộp dòng ngắt giữa câu, giữ công thức.
3. Hoàn tác (Ctrl+Z) đưa văn bản về như trước khi làm sạch.
4. Từ điển: thêm mục -> lưu JSON -> pipeline đọc đúng -> tắt -> không thay.
5. Từ điển đổi -> âm thanh đã tổng hợp bị vô hiệu (bấm Chuyển đổi lại).

Chạy: .venv\\Scripts\\python.exe packaging\\probe_editor_tools.py
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

# Cô lập dữ liệu người dùng (license/trial/từ điển) trong thư mục tạm.
_TMP = Path(tempfile.mkdtemp(prefix="ppmitts_probe_"))
os.environ["LOCALAPPDATA"] = str(_TMP)

from core import dictionary                       # noqa: E402
from core.licensing import store                  # noqa: E402
from core.text_pipeline import prepare_for_tts     # noqa: E402
from ui.main_window import MainWindow              # noqa: E402

MESSY = "Hôm nay trời rất\nđẹp và mát mẻ.\n\n\n\nTa có 1 + 1 = 2.\n[nghỉ 2s]\nCâu cuối."
EXPECTED_CLEAN = ("Hôm nay trời rất đẹp và mát mẻ.\n\n"
                  "Ta có 1 + 1 = 2.\n[nghỉ 2s]\nCâu cuối.")


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
    app.geometry("1200x740")
    pump(app, 1.2)

    # ── 1. Sidebar + TagBar + phím tắt ──
    tb = app.topbar
    buttons = {
        "dict": bool(app.tag_bar.dict_btn and app.tag_bar.dict_btn.winfo_exists()),
        "clean": bool(app.tag_bar.clean_btn and app.tag_bar.clean_btn.winfo_exists()),
    }
    print("[tagbar]", buttons, flush=True)
    if not all(buttons.values()):
        print("[tagbar] LOI: thieu nut Tu dien / Lam sach", flush=True)
        ok = False
    keys = {k: bool(app.bind(k)) for k in
            ("<Control-Shift-D>", "<Control-Shift-K>")}
    print("[key]", keys, flush=True)
    if not all(keys.values()):
        print("[key] LOI: thieu phim tat Tu dien / Lam sach", flush=True)
        ok = False

    # ── 2. Làm sạch ──
    app.textbox.set_text(MESSY)
    app.update()
    app._clean_text()
    pump(app, 0.2)
    cleaned = app.textbox.get_text()
    print("[clean] ->", repr(cleaned), flush=True)
    if cleaned != EXPECTED_CLEAN:
        print("[clean] LOI: ket qua khong dung", flush=True)
        ok = False

    # ── 3. Hoàn tác ──
    undone = app.textbox.undo()
    pump(app, 0.2)
    back = app.textbox.get_text()
    print("[undo] ok =", undone, "| khop ban dau =", back == MESSY, flush=True)
    if not undone or back != MESSY:
        print("[undo] LOI: hoan tac khong dua ve van ban truoc do", flush=True)
        ok = False

    # ── 4. Từ điển ──
    dict_path = dictionary.dictionary_path()
    dictionary.save({"ver": 1, "enabled": True, "entries": [
        {"from": "KTX", "to": "ký túc xá"},
        {"from": "TP.HCM", "to": "thành phố Hồ Chí Minh"},
    ]}, dict_path)
    dictionary.invalidate_cache()
    on_disk = json.loads(dict_path.read_text(encoding="utf-8"))
    print("[dict] file:", dict_path.name, "| so muc:", len(on_disk["entries"]))
    prepared = prepare_for_tts("Về KTX ở TP.HCM")
    print("[dict] prepare:", prepared, flush=True)
    if prepared != "Về ký túc xá ở thành phố Hồ Chí Minh.":
        print("[dict] LOI: pipeline khong ap dung tu dien", flush=True)
        ok = False
    # Không thay trong thẻ
    if prepare_for_tts("Chờ [nghỉ 2s]") != "Chờ [nghỉ 2s].":
        print("[dict] LOI: tu dien lam hong the", flush=True)
        ok = False

    # Tắt từ điển -> không thay nữa
    dictionary.save({"ver": 1, "enabled": False, "entries": [
        {"from": "KTX", "to": "ký túc xá"}]}, dict_path)
    dictionary.invalidate_cache()
    if prepare_for_tts("Về KTX") != "Về KTX.":
        print("[dict] LOI: tat tu dien nhung van thay", flush=True)
        ok = False
    else:
        print("[dict] tat -> giu nguyen 'KTX' OK", flush=True)

    # ── 5. Đổi từ điển vô hiệu hoá âm thanh đã tổng hợp ──
    app._synth_text = "nội dung cũ"
    app._on_dictionary_changed()
    app.update()
    invalidated = app._synth_text is None
    print("[dict] vo hieu audio cu:", invalidated,
          "| status:", tb.status_label.cget("text"), flush=True)
    if not invalidated:
        print("[dict] LOI: doi tu dien khong vo hieu audio cu", flush=True)
        ok = False

    app.destroy()
    print("\nKẾT QUẢ:", "OK" if ok else "LỖI", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
