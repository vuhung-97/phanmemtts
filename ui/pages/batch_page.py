from __future__ import annotations

import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from audio import exporter
from audio.speed import apply_speed
from core.batch import BatchPart, parse_batch, part_filename, write_zip
from core.licensing import guard
from engine.tts_engine import TtsEngine
from ui import theme
from ui.shell.page import Page
from ui.ui_kit import Button, Card, SectionTitle


class BatchPage(Page):
    """Trang Hàng loạt: marker [P1], [P2]… → mỗi phần một tệp, tuỳ chọn .zip."""

    def __init__(self, master, ctx, **kwargs) -> None:
        super().__init__(master, ctx, page_id="batch", title="Chuyển đổi hàng loạt",
                         subtitle="Mỗi marker [P1], [P2]… ở đầu dòng là một tệp",
                         **kwargs)
        self._parts: list[BatchPart] = []
        self._includes: list[ctk.BooleanVar] = []
        self._running = False
        self._cancel = threading.Event()
        self._progress: dict = {"text": "", "index": 0, "total": 0, "done": False,
                                "error": "", "files": [], "zip": ""}
        self._parse_job = None

        Button(self.header.actions, text="Mở .txt", variant="secondary",
               command=self._open_file).pack(side="left", padx=(0, theme.SPACE_SM))
        self.start_btn = Button(self.header.actions, text="Xuất các phần",
                                variant="primary", command=self._start)
        self.start_btn.pack(side="left")

        self.body.grid_columnconfigure(0, weight=3, uniform="batch")
        self.body.grid_columnconfigure(1, weight=2, uniform="batch")
        self.body.grid_rowconfigure(0, weight=1)

        # ── Trái: văn bản nguồn ──
        left = Card(self.body, padding=theme.SPACE_MD)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, theme.SPACE_MD))
        lbox = left.content
        lbox.grid_rowconfigure(1, weight=1)
        lbox.grid_columnconfigure(0, weight=1)
        SectionTitle(lbox, "Văn bản nguồn",
                     "Dòng bắt đầu bằng [P1], [P2]…").grid(row=0, column=0,
                                                          sticky="w")
        self.editor = ctk.CTkTextbox(
            lbox, fg_color=theme.INPUT_BG, text_color=theme.INPUT_TEXT,
            border_width=1, border_color=theme.BORDER, corner_radius=theme.RADIUS_SM,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE), wrap="word",
        )
        self.editor.grid(row=1, column=0, pady=(theme.SPACE_SM, 0), sticky="nsew")
        self.editor.bind("<KeyRelease>", lambda _e: self._schedule_parse())
        self._fill_from_editor_source()

        # ── Phải: danh sách + tuỳ chọn ──
        right = ctk.CTkFrame(self.body, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(0, weight=1)
        right.grid_columnconfigure(0, weight=1)

        parts_card = Card(right, padding=theme.SPACE_MD)
        parts_card.grid(row=0, column=0, sticky="nsew")
        pbox = parts_card.content
        pbox.grid_rowconfigure(2, weight=1)
        pbox.grid_columnconfigure(0, weight=1)

        SectionTitle(pbox, "Các phần sẽ xuất").grid(row=0, column=0, sticky="w")

        mid = ctk.CTkFrame(pbox, fg_color="transparent")
        mid.grid(row=1, column=0, pady=(theme.SPACE_XS, theme.SPACE_SM), sticky="ew")
        mid.grid_columnconfigure(0, weight=1)
        self.summary_label = ctk.CTkLabel(
            mid, text="", anchor="w", text_color=theme.TEXT_DIM,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
        )
        self.summary_label.grid(row=0, column=0, sticky="w")
        Button(mid, text="Tất cả", variant="ghost", size="sm",
               command=lambda: self._set_all(True)).grid(row=0, column=1, padx=2)
        Button(mid, text="Bỏ", variant="ghost", size="sm",
               command=lambda: self._set_all(False)).grid(row=0, column=2)

        self._list = ctk.CTkScrollableFrame(pbox, fg_color=theme.SURFACE)
        self._list.grid(row=2, column=0, sticky="nsew")
        self._list.grid_columnconfigure(0, weight=1)

        options = Card(right, padding=theme.SPACE_MD)
        options.grid(row=1, column=0, sticky="ew", pady=(theme.SPACE_MD, 0))
        obox = options.content
        obox.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(obox, text="Tên tệp", anchor="w",
                     text_color=theme.TEXT_DIM,
                     font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2)).grid(
            row=0, column=0, sticky="w")
        self.base_entry = self._entry(obox, "bai_doc", width=120)
        self.base_entry.grid(row=1, column=0, pady=(2, theme.SPACE_SM), sticky="ew")

        ctk.CTkLabel(obox, text="Thư mục lưu", anchor="w",
                     text_color=theme.TEXT_DIM,
                     font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2)).grid(
            row=2, column=0, sticky="w")
        folder_row = ctk.CTkFrame(obox, fg_color="transparent")
        folder_row.grid(row=3, column=0, pady=(2, theme.SPACE_SM), sticky="ew")
        folder_row.grid_columnconfigure(0, weight=1)
        self.folder_entry = self._entry(folder_row, "", width=120)
        self.folder_entry.grid(row=0, column=0, sticky="ew")
        Button(folder_row, text="…", variant="secondary", size="sm", width=34,
               command=self._choose_folder).grid(row=0, column=1,
                                                 padx=(theme.SPACE_XS, 0))

        fmt = ctk.CTkFrame(obox, fg_color="transparent")
        fmt.grid(row=4, column=0, sticky="w")
        self.format_var = ctk.StringVar(value="mp3")
        for value, label in (("mp3", "MP3 (nhẹ)"), ("wav", "WAV")):
            ctk.CTkRadioButton(
                fmt, text=label, variable=self.format_var, value=value,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
                text_color=theme.TEXT, fg_color=theme.PRIMARY,
                hover_color=theme.PRIMARY_HOVER,
            ).pack(side="left", padx=(0, theme.SPACE_MD))

        self.zip_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            obox, text="Đóng gói 1 tệp .zip", variable=self.zip_var,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
            text_color=theme.TEXT, fg_color=theme.PRIMARY,
            hover_color=theme.PRIMARY_HOVER, corner_radius=4,
        ).grid(row=5, column=0, pady=(theme.SPACE_XS, 0), sticky="w")

        self.progress = ctk.CTkProgressBar(obox, height=8)
        self.progress.set(0)
        self.progress.grid(row=6, column=0, pady=(theme.SPACE_MD, theme.SPACE_XS),
                           sticky="ew")
        self.status_label = ctk.CTkLabel(
            obox, text="", anchor="w", justify="left", wraplength=330,
            text_color=theme.TEXT_DIM,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
        )
        self.status_label.grid(row=7, column=0, sticky="w")

        self._parse()

    # ── helper ──

    @staticmethod
    def _entry(parent, placeholder: str, width: int = 200) -> ctk.CTkEntry:
        return ctk.CTkEntry(
            parent, height=34, width=width, placeholder_text=placeholder,
            fg_color=theme.INPUT_BG, text_color=theme.INPUT_TEXT,
            placeholder_text_color=theme.INPUT_PLACEHOLDER,
            border_color=theme.BORDER, border_width=1,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
        )

    def _fill_from_editor_source(self) -> None:
        """Lấy văn bản đang soạn ở trang Đọc văn bản (nếu có)."""
        try:
            text = self.ctx.textbox.get_text()
        except Exception:
            text = ""
        if text:
            self.editor.insert("1.0", text)

    # ── tách phần ──

    def _schedule_parse(self) -> None:
        if self._running:
            return
        if self._parse_job is not None:
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
            ctk.CTkLabel(self._list, text="Chưa có nội dung.",
                         text_color=theme.TEXT_DIM,
                         font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1)).grid(
                row=0, column=0, padx=theme.SPACE_SM,
                pady=theme.SPACE_LG, sticky="w")
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
                text_color=theme.TEXT, fg_color=theme.PRIMARY,
                hover_color=theme.PRIMARY_HOVER, corner_radius=4, width=60,
            ).grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(
                row, text=f"{part.sentence_count} câu",
                text_color=theme.TEXT_DIM,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
            ).grid(row=0, column=1, padx=(theme.SPACE_XS, theme.SPACE_SM), sticky="e")
        total_chars = sum(p.char_count for p in self._parts)
        self.summary_label.configure(
            text=f"{len(self._parts)} phần · {total_chars} ký tự")

    def _set_all(self, value: bool) -> None:
        for var in self._includes:
            var.set(value)

    def _selected_parts(self) -> list[BatchPart]:
        return [part for part, var in zip(self._parts, self._includes) if var.get()]

    # ── tệp / thư mục ──

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

    # ── chạy ──

    def _start(self) -> None:
        if self._running:
            self._cancel.set()
            self._set_status("Đang dừng sau phần hiện tại…", theme.TEXT_DIM)
            return
        if not self.ctx._ensure_license("xuất nhiều tệp"):
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
        model = self.ctx._selected_model()
        if model is None:
            self._set_status("Chưa chọn được giọng đọc.", theme.ERROR)
            return

        self._running = True
        self._cancel.clear()
        self._progress = {"text": "Đang chuẩn bị…", "index": 0, "total": len(parts),
                          "done": False, "error": "", "files": [], "zip": ""}
        self.progress.set(0)
        self.start_btn.configure(text="⏹  Dừng", fg_color=theme.DANGER,
                                 hover_color=theme.DANGER_HOVER)
        threading.Thread(target=self._worker, args=(
            parts, folder, self.base_entry.get().strip(),
            self.format_var.get(), bool(self.zip_var.get()),
            model, self.ctx._model_manager,
            self.ctx.topbar.get_speed()), daemon=True).start()
        self.after(100, self._poll)

    def _worker(self, parts, folder, base, ext, make_zip, model, manager,
                speed) -> None:
        out_dir = Path(folder)
        try:
            if not guard.check_startup().active:
                self._progress.update(text="Thiết bị chưa kích hoạt — không thể "
                                           "xuất file.", done=True, error="license")
                return
            self._progress["text"] = "Đang nạp giọng đọc…"
            tts = manager.load_tts(model)
            engine = TtsEngine(tts)
            sr = engine.sample_rate
            used: set[str] = set()
            files: list[str] = []
            for i, part in enumerate(parts, start=1):
                if self._cancel.is_set():
                    self._progress.update(text=f"Đã dừng sau {i - 1}/{len(parts)} "
                                               f"phần.", done=True)
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
                self._progress.update(text="Không tạo được tệp nào (văn bản rỗng?).",
                                      done=True, error="empty")
                return
            if make_zip and len(files) > 1:
                self._progress["text"] = "Đang đóng gói .zip…"
                archive = write_zip(files, out_dir / f"{base or 'audio'}.zip")
                self._progress["zip"] = str(archive)
            self._progress.update(
                text=f"Xong: {len(files)} tệp"
                     + (" + 1 zip" if self._progress["zip"] else "")
                     + f" → {out_dir}",
                done=True)
        except Exception as exc:      # pragma: no cover - phụ thuộc model
            self._progress.update(text=f"Lỗi: {exc}", done=True, error=str(exc))

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
        self.start_btn.configure(text="Xuất các phần", fg_color=theme.PRIMARY,
                                 hover_color=theme.PRIMARY_HOVER)
        if state.get("error"):
            return
        self.progress.set(1.0)
        self._set_status(state.get("text", ""), theme.SUCCESS)
        self.ctx.shell.status(state.get("text", ""), theme.SUCCESS)

    def _set_status(self, text: str, color: str = theme.TEXT_DIM) -> None:
        self.status_label.configure(text=text, text_color=color)

    # ── vòng đời ──

    def on_show(self) -> None:
        if not self.editor.get("1.0", "end-1c").strip():
            self._fill_from_editor_source()
            self._parse()
