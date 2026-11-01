"""Probe P4: trang Hội thoại nhiều giọng (parse, gán giọng, tạo, xuất).

Chạy: .venv\\Scripts\\python.exe packaging\\probe_dialogue.py
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

_TMP = Path(tempfile.mkdtemp(prefix="ppmitts_dialogue_"))
os.environ["LOCALAPPDATA"] = str(_TMP)

from core import dialogue                    # noqa: E402
from core.licensing import (fingerprint, guard, shortcode,  # noqa: E402
                            store)
from ui.main_window import MainWindow         # noqa: E402

SCRIPT = """# Bản tin mẫu
An: Xin chào, tôi là An.
Bình: Chào An. Hôm nay có gì mới?
An: Có ba tin đáng chú ý.
"""


def pump(app, seconds: float = 0.3) -> None:
    end = time.time() + seconds
    while time.time() < end:
        app.update()
        time.sleep(0.02)


def main() -> int:
    ok = True
    store.configure(_TMP / "license", registry=False)
    guard.reset_cache()
    guard.install(shortcode.issue(fingerprint.machine24(),
                                  shortcode.KIND_LIFETIME), now=time.time())

    app = MainWindow()
    if getattr(app, "_prompt_job", None):
        app.after_cancel(app._prompt_job)
    app.geometry("1280x800")
    pump(app, 0.8)

    if not app.shell.has_page("dialogue"):
        print("LOI: chua dang ky page dialogue")
        return 1
    app.shell.show("dialogue")
    pump(app, 0.3)
    page = app.dialogue_page
    print("[page] hien tai:", app.shell.current_page.page_id)
    labels = {
        "open": page.open_btn.cget("text"),
        "sample": page.sample_btn.cget("text"),
        "export": page.export_btn.cget("text"),
        "create": page.create_btn.cget("text"),
    }
    print("[button]", labels)
    if "Mở file" not in labels["open"] or "📁" not in labels["open"]:
        print("[button] LOI: nut mo file thieu icon/ten")
        ok = False
    if "📄" not in labels["sample"] or "💾" not in labels["export"]:
        print("[button] LOI: nut Dan mau / Xuat file thieu icon")
        ok = False

    # ── Parse + lỗi ──
    page.editor.set_text("An: ok\nDòng thiếu tên.")
    page._parse()
    pump(app, 0.1)
    issues = [str(i) for i in page._script.issues]
    print("[error] issues:", issues, "| create:", page.create_btn.cget("state"))
    if not issues or page.create_btn.cget("state") != "disabled":
        print("[error] LOI: khong chan dong thieu ten")
        ok = False

    # ── Parse hợp lệ + gán giọng ──
    page.editor.set_text(SCRIPT)
    page._parse()
    pump(app, 0.1)
    print("[parse] speakers:", page._script.speakers,
          "| turns:", len(page._script.turns), "| cast:", page._cast)
    if page._script.speakers != ["An", "Bình"] or not page._script.ok:
        print("[parse] LOI: parse sai")
        ok = False
    if len(page._cast) < 2 or any(not v for v in page._cast.values()):
        print("[parse] LOI: chua gan du giong")
        ok = False

    # ── Mở từ .docx ──
    from docx import Document

    doc = Document()
    for line in SCRIPT.splitlines():
        doc.add_paragraph(line)
    docx_path = _TMP / "kich_ban.docx"
    doc.save(docx_path)
    page.load_script_file(str(docx_path))
    pump(app, 0.2)
    print("[docx] speakers:", page._script.speakers,
          "| ok:", page._script.ok)
    if page._script.speakers != ["An", "Bình"] or not page._script.ok:
        print("[docx] LOI: khong doc duoc kich ban .docx")
        ok = False

    # ── Nháp tự lưu ──
    page._on_text_changed()
    pump(app, 0.9)
    draft = dialogue.load_draft()
    print("[draft] luu nhap:", bool(draft), len(draft))
    if not draft:
        print("[draft] LOI: khong tu luu nhap")
        ok = False

    # ── Tạo hội thoại ──
    page._create()
    deadline = time.time() + 180
    while page._busy and time.time() < deadline:
        app.update()
        time.sleep(0.05)
    pump(app, 0.4)
    timeline = page._timeline
    print("[create] busy:", page._busy, "| cau:",
          len(timeline.sentences) if timeline else 0, "| thoi luong:",
          round(timeline.total_duration, 2) if timeline else 0,
          "| status:", page.status_label.cget("text"))
    if page._busy or timeline is None or len(timeline.sentences) < 3:
        print("[create] LOI: khong tao duoc hoi thoai")
        ok = False
    else:
        # offset ký tự phải trỏ đúng nội dung trong kịch bản
        text = page.editor.get_text()
        first = timeline.sentences[0]
        snippet = text[first.char_start:first.char_end]
        print("[timeline] cau 1:", repr(snippet), "| start:",
              round(first.start_sec, 2))
        if not snippet:
            print("[timeline] LOI: char offset sai")
            ok = False

    # ── Xuất file ──
    if page._store is not None:
        from audio import exporter
        out = _TMP / "hoi_thoai.mp3"
        exporter.export_source(page._store, page._sample_rate, out)
        size = out.stat().st_size if out.exists() else 0
        print("[export] file:", out.name, size, "bytes")
        if size <= 0:
            print("[export] LOI: file rong")
            ok = False

    # ── Waveform chạy theo thời gian ──
    bar = app.shell.player_bar
    page._player.stop()
    bar.set_position(0.5)
    app.update()
    print("[wave] peaks:", None if bar.waveform._peaks is None
          else len(bar.waveform._peaks), "| position:",
          bar.waveform._position)
    if bar.waveform._peaks is None or abs(bar.waveform._position - 0.5) > 0.05:
        print("[wave] LOI: waveform khong cap nhat vi tri")
        ok = False

    # ── Lịch sử sau khi xuất ──
    import ui.pages.dialogue_page as dp

    out2 = _TMP / "export_test.mp3"
    dp.filedialog.asksaveasfilename = lambda **_kw: str(out2)
    before = len(app._history.entries)
    page._export()
    pump(app, 0.3)
    after = len(app._history.entries)
    print("[history]", before, "->", after, "| file:", out2.exists())
    if after != before + 1:
        print("[history] LOI: khong ghi lich su hoi thoai")
        ok = False

    # ── Chuyển trang qua lại ──
    app.shell.show("text")
    pump(app, 0.2)
    app.shell.show("dialogue")
    pump(app, 0.2)
    kept = page.editor.get_text().startswith("# Bản tin mẫu")
    print("[nav] giu kich ban:", kept,
          "| speed o text/dialogue:", app.shell.player_bar.speed_combo.cget("state"))
    if not kept:
        print("[nav] LOI: mat kich ban khi chuyen trang")
        ok = False

    app.destroy()
    print("\nKẾT QUẢ:", "OK" if ok else "LỖI", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
