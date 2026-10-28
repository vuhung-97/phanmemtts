"""Hộp thoại chuyển đổi hàng loạt theo marker ``[P1]``, ``[P2]``…

Mỗi marker -> một tệp audio. Xuất ra thư mục (hoặc đóng gói .zip).
Dùng lại model/giọng đang chọn ở cửa sổ chính; không nạp model lần 2.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable

import customtkinter as ctk

from audio import exporter
from audio.speed import apply_speed
from core.batch import BatchPart, parse_batch, part_filename, write_zip
from core.licensing import guard
from engine.tts_engine import TtsEngine
from ui import theme


class BatchDialog(ctk.CTkToplevel):
    """Tách phần -> chọn giọng/định dạng -> xuất nhiều tệp hoặc 1 .zip."""

    def __init__(self, master, text: str = "", model=None,
                 model_manager=None, voice_name: str = "", speed: float = 1.0,
                 on_done: Callable[[str], None] | None = None) -> None:
        super().__init__(master)
        self.title("Chuyển đổi hàng loạt")
        self.geometry("860x700")
        self.minsize(720, 560)
        self.configure(fg_color=theme.DIALOG_BG)
        self.transient(master)
        self.grab_set()

        self._model = model
        self._model_manager = model_manager
        self._voice_name = voice_name
        self._speed = speed
        self._on_done = on_done

        self._parts: list[BatchPart] = []
        self._includes: list[ctk.BooleanVar] = []
        self._running = False
        self._cancel = threading.Event()
        self._progress: dict = {"text": "", "index": 0, "total": 0, "done": False,
                                "error": "", "files": [], "zip": ""}

        self._build_ui(text)
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.bind("<Escape>", lambda _: self._close())
        self._parse()

    # ── UI ──

    def _build_ui(self, text: str) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, padx=18, pady=(14, 4), sticky="ew")
        head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            head, text="Chuyển đổi hàng loạt",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE + 3, "bold"),
            text_color=theme.TEXT,
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            head,
            text=("Đặt marker [P1], [P2]… ở ĐẦU DÒNG — mỗi marker thành một tệp. "
                  f"Giọng: {self._voice_name or '—'} · Tốc độ: {self._speed:g}x"),
            text_color=theme.TEXT_DIM,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
        ).grid(row=1, column=0, columnspan=2, pady=(2, 0), sticky="w")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, padx=18, pady=4, sticky="nsew")
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(1, weight=1)

        # ── Trái: văn bản nguồn ──
        src_head = ctk.CTkFrame(body, fg_color="transparent")
        src_head.grid(row=0, column=0, padx=(0, 8), sticky="ew")
        src_head.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            src_head, text="Văn bản nguồn",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
            text_color=theme.TEXT,
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            src_head, text="📂 Mở .txt", height=28, width=90,
            fg_color="transparent", border_width=1, border_color=theme.SIDEBAR_DIVIDER,
            text_color=theme.TEXT, hover_color=theme.SURFACE, corner_radius=6,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            command=self._open_file,
        ).grid(row=0, column=1, sticky="e")

        self.editor = ctk.CTkTextbox(
            body, fg_color=theme.INPUT_BG, text_color=theme.INPUT_TEXT,
            border_width=1, border_color=theme.SIDEBAR_DIVIDER,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE), wrap="word",
        )
        self.editor.grid(row=1, column=0, padx=(0, 8), pady=(4, 0), sticky="nsew")
        if text:
            self.editor.insert("1.0", text)
        self.editor.bind("<KeyRelease>", lambda _e: self._schedule_parse())

        # ── Phải: danh sách phần ──
        right = ctk.CTkFrame(body, fg_color=theme.SURFACE, corner_radius=8,
                             border_width=1, border_color=theme.SIDEBAR_DIVIDER)
        right.grid(row=0, column=1, rowspan=2, pady=(0, 0), sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            right, text="Các phần sẽ xuất",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
            text_color=theme.TEXT,
        ).grid(row=0, column=0, padx=10, pady=(8, 2), sticky="w")

        mid = ctk.CTkFrame(right, fg_color="transparent")
        mid.grid(row=1, column=0, padx=10, pady=(0, 4), sticky="ew")
        self.summary_label = ctk.CTkLabel(
            mid, text="", text_color=theme.TEXT_DIM, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
        )
        self.summary_label.pack(side="left")
        ctk.CTkButton(
            mid, text="Tất cả", height=24, width=60,
            fg_color="transparent", border_width=1, border_color=theme.SIDEBAR_DIVIDER,
            text_color=theme.TEXT, hover_color=theme.SURFACE, corner_radius=6,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
            command=lambda: self._set_all(True),
        ).pack(side="right", padx=(4, 0))
        ctk.CTkButton(
            mid, text="Bỏ", height=24, width=44,
            fg_color="transparent", border_width=1, border_color=theme.SIDEBAR_DIVIDER,
            text_color=theme.TEXT, hover_color=theme.SURFACE, corner_radius=6,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
            command=lambda: self._set_all(False),
        ).pack(side="right")

        self._list = ctk.CTkScrollableFrame(right, fg_color=theme.SURFACE)
        self._list.grid(row=2, column=0, padx=4, pady=(0, 6), sticky="nsew")
        self._list.grid_columnconfigure(0, weight=1)

        # ── Tuỳ chọn xuất ──
        opts = ctk.CTkFrame(self, fg_color=theme.SURFACE, corner_radius=8,
                            border_width=1, border_color=theme.SIDEBAR_DIVIDER)
        opts.grid(row=2, column=0, padx=18, pady=4, sticky="ew")
        opts.grid_columnconfigure(1, weight=1)
        opts.grid_columnconfigure(3, weight=1)

        self.base_entry = self._entry(opts, "Tên tệp", 0, 0, "bai_doc")
        self.folder_entry = self._entry(opts, "Thư mục lưu", 0, 2, "")

        self.format_var = ctk.StringVar(value="mp3")
        fmt = ctk.CTkFrame(opts, fg_color="transparent")
        fmt.grid(row=1, column=0, columnspan=2, padx=10, pady=(2, 8), sticky="w")
        for value, label in (("mp3", "MP3 (nhẹ)"), ("wav", "WAV (gốc)")):
            ctk.CTkRadioButton(
                fmt, text=label, variable=self.format_var, value=value,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
                text_color=theme.TEXT, fg_color=theme.ACCENT,
                hover_color=theme.ACCENT_HOVER,
            ).pack(side="left", padx=(0, 12))

        self.zip_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            opts, text="Đóng gói 1 tệp .zip", variable=self.zip_var,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
            text_color=theme.TEXT, fg_color=theme.ACCENT, hover_color=theme.ACCENT,
            corner_radius=4,
        ).grid(row=1, column=2, padx=10, pady=(2, 8), sticky="w")

        ctk.CTkButton(
            opts, text="Chọn thư mục…", height=28, width=110,
            fg_color="transparent", border_width=1, border_color=theme.SIDEBAR_DIVIDER,
            text_color=theme.TEXT, hover_color=theme.SURFACE, corner_radius=6,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
            command=self._choose_folder,
        ).grid(row=0, column=4, padx=(0, 10), pady=(10, 0))

        # ── Chân: tiến trình + nút ──
        foot = ctk.CTkFrame(self, fg_color="transparent")
        foot.grid(row=3, column=0, padx=18, pady=(4, 14), sticky="ew")
        foot.grid_columnconfigure(0, weight=1)

        self.progress = ctk.CTkProgressBar(foot, height=8)
        self.progress.set(0)
        self.progress.grid(row=0, column=0, columnspan=3, sticky="ew")
        self.status_label = ctk.CTkLabel(
            foot, text="", text_color=theme.TEXT_DIM, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
        )
        self.status_label.grid(row=1, column=0, pady=(4, 0), sticky="w")

        self.close_btn = ctk.CTkButton(
            foot, text="Đóng", height=34, width=90,
            fg_color="transparent", border_width=1, border_color=theme.SIDEBAR_DIVIDER,
            text_color=theme.TEXT, hover_color=theme.SURFACE, corner_radius=8,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            command=self._close,
        )
        self.close_btn.grid(row=1, column=1, padx=(6, 6), pady=(4, 0))
        self.start_btn = ctk.CTkButton(
            foot, text="⚡  Xuất các phần", height=34, width=150,
            fg_color=theme.SUCCESS, hover_color=theme.SUCCESS_HOVER,
            text_color="#ffffff", corner_radius=8,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
            command=self._start,
        )
        self.start_btn.grid(row=1, column=2, pady=(4, 0))

    def _entry(self, parent, label: str, row: int, column: int,
               placeholder: str) -> ctk.CTkEntry:
        ctk.CTkLabel(
            parent, text=label, text_color=theme.TEXT_DIM, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2, "bold"),
        ).grid(row=row, column=column, padx=(10, 4), pady=(10, 0), sticky="w")
        entry = ctk.CTkEntry(
            parent, height=30, placeholder_text=placeholder,
            fg_color=theme.INPUT_BG, text_color=theme.INPUT_TEXT,
            placeholder_text_color=theme.INPUT_PLACEHOLDER,
            border_color=theme.SIDEBAR_DIVIDER, border_width=1,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
        )
        entry.grid(row=row, column=column + 1, padx=(0, 10), pady=(10, 0), sticky="ew")
        return entry

    # ── Tách phần ──

    def _schedule_parse(self) -> None:
        if self._running:
            return
        if getattr(self, "_parse_job", None):
            self.after_cancel(self._parse_job)
        self._parse_job = self.after(300, self._parse)

    def _parse(self) -> None:
        self._parse_job = None
        text = self.editor.get("1.0", "end-1c")
        self._parts = parse_batch(text)
        self._render_parts()

    def _render_parts(self) -> None:
        for child in self._list.winfo_children():
            child.destroy()
        self._includes = []

        if not self._parts:
            ctk.CTkLabel(
                self._list, text="Chưa có nội dung.",
                text_color=theme.TEXT_DIM,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            ).grid(row=0, column=0, padx=10, pady=16, sticky="w")
            self.summary_label.configure(text="0 phần")
            return

        for index, part in enumerate(self._parts):
            var = ctk.BooleanVar(value=True)
            self._includes.append(var)
            row = ctk.CTkFrame(self._list, fg_color="transparent")
            row.grid(row=index, column=0, padx=2, pady=1, sticky="ew")
            row.grid_columnconfigure(0, weight=1)
            ctk.CTkCheckBox(
                row, text=part.label, variable=var,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
                text_color=theme.TEXT, fg_color=theme.ACCENT,
                hover_color=theme.ACCENT, corner_radius=4, width=60,
            ).grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(
                row, text=f"{part.sentence_count} câu · {part.char_count} ký tự",
                text_color=theme.TEXT_DIM,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
            ).grid(row=0, column=1, padx=(4, 6), sticky="e")

        total_chars = sum(p.char_count for p in self._parts)
        self.summary_label.configure(
            text=f"{len(self._parts)} phần · {total_chars} ký tự")

    def _set_all(self, value: bool) -> None:
        for var in self._includes:
            var.set(value)

    def _selected_parts(self) -> list[BatchPart]:
        return [part for part, var in zip(self._parts, self._includes) if var.get()]

    # ── Nhập / chọn thư mục ──

    def _open_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Mở văn bản", filetypes=[("Văn bản", "*.txt"), ("Tất cả", "*.*")],
            parent=self,
        )
        if not path:
            return
        try:
            content = Path(path).read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as exc:
            messagebox.showerror("Không đọc được tệp", str(exc), parent=self)
            return
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", content)
        self._parse()

    def _choose_folder(self) -> None:
        path = filedialog.askdirectory(title="Chọn thư mục lưu", parent=self)
        if path:
            self.folder_entry.delete(0, "end")
            self.folder_entry.insert(0, path)

    # ── Chạy ──

    def _start(self) -> None:
        if self._running:
            self._cancel.set()
            self._set_status("Đang dừng sau phần hiện tại…", theme.TEXT_DIM)
            return
        parts = self._selected_parts()
        if not parts:
            self._set_status("Chưa chọn phần nào để xuất.", theme.ERROR)
            return
        folder = self.folder_entry.get().strip()
        if not folder:
            self._choose_folder()
            folder = self.folder_entry.get().strip()
        if not folder:
            self._set_status("Chọn thư mục lưu trước khi xuất.", theme.ERROR)
            return
        if not Path(folder).is_dir():
            self._set_status("Thư mục lưu không tồn tại.", theme.ERROR)
            return
        if self._model is None or self._model_manager is None:
            self._set_status("Chưa chọn được giọng đọc.", theme.ERROR)
            return

        self._running = True
        self._cancel.clear()
        self._progress = {"text": "Đang chuẩn bị…", "index": 0, "total": len(parts),
                          "done": False, "error": "", "files": [], "zip": ""}
        self.progress.set(0)
        self.start_btn.configure(text="⏹  Dừng", fg_color=theme.ERROR,
                                 hover_color="#b91c1c")
        self.close_btn.configure(state="disabled")
        threading.Thread(target=self._worker, args=(
            parts, folder, self.base_entry.get().strip(),
            self.format_var.get(), bool(self.zip_var.get())), daemon=True).start()
        self.after(100, self._poll)

    def _worker(self, parts: list[BatchPart], folder: str, base: str,
                ext: str, make_zip: bool) -> None:
        out_dir = Path(folder)
        try:
            if not guard.check_startup().active:
                self._fail("Thiết bị chưa kích hoạt — không thể xuất file.")
                return
            self._progress["text"] = "Đang nạp giọng đọc…"
            tts = self._model_manager.load_tts(self._model)
            engine = TtsEngine(tts)
            sr = engine.sample_rate
            used: set[str] = set()
            files: list[str] = []
            speed = self._speed

            for i, part in enumerate(parts, start=1):
                if self._cancel.is_set():
                    self._progress["text"] = f"Đã dừng sau {i - 1}/{len(parts)} phần."
                    self._progress["done"] = True
                    return
                self._progress.update(index=i - 1, total=len(parts),
                                      text=f"Đang tạo {part.label} ({i}/{len(parts)})…")
                if part.sentence_count == 0:
                    continue
                waveform, _timeline = engine.synthesize(part.text, speed=1.0)
                if speed and abs(speed - 1.0) > 1e-9:
                    waveform = apply_speed(waveform, speed)
                name = part_filename(part, base, f".{ext}", used)
                out = exporter.export(waveform, sr, out_dir / name)
                files.append(str(out))
                self._progress.update(index=i, files=list(files))

            if not files:
                self._fail("Không tạo được tệp nào (văn bản rỗng?).")
                return
            if make_zip and len(files) > 1:
                zip_name = f"{base or 'audio'}.zip"
                self._progress["text"] = "Đang đóng gói .zip…"
                archive = write_zip(files, out_dir / zip_name)
                self._progress["zip"] = str(archive)
            self._progress.update(
                text=f"Xong: {len(files)} tệp"
                     + (f" + 1 zip" if self._progress["zip"] else "")
                     + f" → {out_dir}",
                done=True,
            )
        except Exception as exc:      # pragma: no cover - phụ thuộc model
            self._fail(str(exc))

    def _fail(self, message: str) -> None:
        self._progress.update(text=f"Lỗi: {message}", error=message, done=True)

    def _poll(self) -> None:
        state = self._progress
        total = max(1, int(state.get("total") or 1))
        self.progress.set(min(1.0, float(state.get("index") or 0) / total))
        self._set_status(state.get("text", ""),
                         theme.ERROR if state.get("error") else theme.TEXT_DIM)
        if not state.get("done"):
            self.after(100, self._poll)
            return

        self._running = False
        self.start_btn.configure(text="⚡  Xuất các phần", fg_color=theme.SUCCESS,
                                 hover_color=theme.SUCCESS_HOVER)
        self.close_btn.configure(state="normal")
        if state.get("error"):
            return
        self.progress.set(1.0)
        self._set_status(state.get("text", ""), theme.SUCCESS)
        if self._on_done is not None:
            self._on_done(state.get("text", ""))

    def _set_status(self, text: str, color: str = theme.TEXT_DIM) -> None:
        self.status_label.configure(text=text, text_color=color)

    def _close(self) -> None:
        if self._running:
            if not messagebox.askyesno(
                    "Đang xuất file",
                    "Đang xuất dở — dừng và đóng?", parent=self):
                return
            self._cancel.set()
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()
