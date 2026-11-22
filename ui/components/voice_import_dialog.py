"""Hộp thoại "Thêm giọng mới": nhập file giọng (.json) hoặc tạo từ mẫu.

Tách khỏi ``voice_manager.py`` để mỗi file nằm dưới giới hạn 32 KB code
object của PyArmor bản miễn phí.

Tab "Tạo giọng mới" có **cam kết bắt buộc** về quyền sử dụng giọng nói
(điều khoản sử dụng của app).
"""

from __future__ import annotations

import threading
from tkinter import filedialog
from typing import Callable

import customtkinter as ctk

from ui import theme

COMMITMENT_TEXT = ("Tôi cam kết đây là giọng của chính tôi hoặc tôi có quyền "
                   "sử dụng giọng này để tạo âm thanh.")


class ImportVoiceDialog(ctk.CTkToplevel):
    """Hộp thoại 2 tab: nhập file giọng có sẵn (.json) / tạo giọng mới từ mẫu."""

    def __init__(self, master, on_import: Callable[[str], bool],
                 on_created: Callable[[str], bool] | None = None,
                 low_memory: bool = False,
                 tts_provider: Callable[[], object] | None = None) -> None:
        super().__init__(master)
        self._low_memory = bool(low_memory)
        # Dùng lại model đang nạp (nếu có) thay vì nạp thêm 1 model ~1 GB.
        self._tts_provider = tts_provider
        self.title("Thêm giọng mới")
        self.geometry("540x700")
        self.resizable(False, False)
        self.configure(fg_color=theme.DIALOG_BG)
        self.transient(master)
        self.grab_set()

        self._on_import = on_import
        self._on_created = on_created
        self._path: str | None = None
        # Tab tạo giọng
        self._sample_path: str | None = None
        self._creating = False
        self._create_result: tuple[bool, str] | None = None

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.bind("<Escape>", lambda _: self._close())

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # 2 nút chuyển tab, mỗi nút 50% chiều rộng dialog
        switch = ctk.CTkFrame(self, fg_color="transparent")
        switch.grid(row=0, column=0, padx=12, pady=(12, 4), sticky="ew")
        switch.grid_columnconfigure((0, 1), weight=1)
        self._tab_btn_import = ctk.CTkButton(
            switch, text="📥  Nhập giọng có sẵn", height=44, corner_radius=10,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE + 1, "bold"),
            command=lambda: self._select_tab("import"),
        )
        self._tab_btn_import.grid(row=0, column=0, padx=(0, 4), sticky="ew")
        self._tab_btn_create = ctk.CTkButton(
            switch, text="🎙  Tạo giọng mới", height=44, corner_radius=10,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE + 1, "bold"),
            command=lambda: self._select_tab("create"),
        )
        self._tab_btn_create.grid(row=0, column=1, padx=(4, 0), sticky="ew")

        self._frame_import = ctk.CTkFrame(self, fg_color="transparent")
        self._frame_import.grid(row=1, column=0, padx=4, sticky="nsew")
        self._frame_import.grid_columnconfigure(0, weight=1)
        self._frame_create = ctk.CTkFrame(self, fg_color="transparent")
        self._frame_create.grid(row=1, column=0, padx=4, sticky="nsew")
        self._frame_create.grid_columnconfigure(0, weight=1)

        self._build_import_tab(self._frame_import)
        self._build_create_tab(self._frame_create)
        self._select_tab("import")

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=2, column=0, padx=20, pady=(4, 16), sticky="ew")
        bottom.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(
            bottom, text="Đóng", height=36,
            fg_color="transparent", border_width=1, border_color=theme.SIDEBAR_DIVIDER,
            text_color=theme.TEXT, hover_color=theme.SURFACE, corner_radius=8,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            command=self._close,
        ).grid(row=0, column=0, sticky="ew")

    def _select_tab(self, which: str) -> None:
        active = {"fg_color": theme.ACCENT, "hover_color": theme.ACCENT_HOVER,
                  "text_color": "#ffffff", "border_width": 0}
        idle = {"fg_color": "transparent", "hover_color": theme.SURFACE,
                "text_color": theme.TEXT_DIM, "border_width": 1,
                "border_color": theme.SIDEBAR_DIVIDER}
        if which == "import":
            self._tab_btn_import.configure(**active)
            self._tab_btn_create.configure(**idle)
            self._frame_import.tkraise()
        else:
            self._tab_btn_import.configure(**idle)
            self._tab_btn_create.configure(**active)
            self._frame_create.tkraise()

    # ── Tab 1: nhập file giọng có sẵn ──

    def _build_import_tab(self, tab) -> None:
        tab.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            tab, text="Nhập file giọng có sẵn (.json)",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE + 2, "bold"),
            text_color=theme.TEXT,
        ).grid(row=0, column=0, padx=12, pady=(12, 2), sticky="w")

        ctk.CTkLabel(
            tab,
            text="B1: bấm “Chọn tệp…” lấy file .json do quản trị viên cấp. "
                 "B2: kiểm tra tên hiện ở dưới. B3: bấm “Nhập giọng”.",
            text_color=theme.TEXT_DIM, font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            wraplength=460, justify="left",
        ).grid(row=1, column=0, padx=12, pady=(0, 10), sticky="w")

        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.grid(row=2, column=0, padx=12, pady=(0, 8), sticky="ew")
        row.grid_columnconfigure(0, weight=1)

        self.path_entry = ctk.CTkEntry(
            row, height=32, placeholder_text="Chưa chọn file giọng...",
            fg_color=theme.INPUT_BG, text_color=theme.INPUT_TEXT,
            placeholder_text_color=theme.INPUT_PLACEHOLDER,
            border_color=theme.SURFACE,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
        )
        self.path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            row, text="Chọn tệp…", height=32, width=100,
            fg_color=theme.BUTTON_BG, hover_color=theme.BUTTON_HOVER,
            text_color=theme.TEXT,
            corner_radius=6, font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            command=self._choose_file,
        ).grid(row=0, column=1)

        self.preview_label = ctk.CTkLabel(
            tab, text="", text_color=theme.TEXT,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE), wraplength=460,
            justify="left",
        )
        self.preview_label.grid(row=3, column=0, padx=12, pady=(0, 4), sticky="w")

        self.error_label = ctk.CTkLabel(
            tab, text="", text_color=theme.ERROR,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1), wraplength=460,
            justify="left",
        )
        self.error_label.grid(row=4, column=0, padx=12, pady=(0, 6), sticky="w")

        self.import_btn = ctk.CTkButton(
            tab, text="⬇  Nhập giọng", height=42, fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER, text_color="#ffffff", corner_radius=10,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE + 1, "bold"),
            state="disabled", command=self._do_import,
        )
        self.import_btn.grid(row=5, column=0, padx=12, pady=(4, 12), sticky="ew")

    # ── Tab 2: tạo giọng mới từ file mẫu âm thanh ──

    def _build_create_tab(self, tab) -> None:
        tab.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            tab, text="Tạo giọng mới từ mẫu âm thanh",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE + 2, "bold"),
            text_color=theme.TEXT,
        ).grid(row=0, column=0, padx=12, pady=(12, 2), sticky="w")

        ctk.CTkLabel(
            tab,
            text="B1: đặt tên giọng. B2: bấm “Chọn mẫu…” lấy file âm thanh "
                 "(wav/mp3/flac, 5–30 giây, 1 người nói rõ, ít ồn/nhạc). "
                 "B3: bấm “Tạo giọng” và chờ ~10 giây.",
            text_color=theme.TEXT_DIM, font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            wraplength=460, justify="left",
        ).grid(row=1, column=0, padx=12, pady=(0, 10), sticky="w")

        self.create_name_entry = ctk.CTkEntry(
            tab, height=32, placeholder_text="Tên giọng mới (vd: Giọng A)...",
            fg_color=theme.INPUT_BG, text_color=theme.INPUT_TEXT,
            placeholder_text_color=theme.INPUT_PLACEHOLDER,
            border_color=theme.SURFACE,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
        )
        self.create_name_entry.grid(row=2, column=0, padx=12, pady=(0, 8), sticky="ew")

        self.create_desc_entry = ctk.CTkEntry(
            tab, height=32, placeholder_text="Mô tả giọng (tùy chọn)...",
            fg_color=theme.INPUT_BG, text_color=theme.INPUT_TEXT,
            placeholder_text_color=theme.INPUT_PLACEHOLDER,
            border_color=theme.SURFACE,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
        )
        self.create_desc_entry.grid(row=3, column=0, padx=12, pady=(0, 8), sticky="ew")

        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.grid(row=4, column=0, padx=12, pady=(0, 8), sticky="ew")
        row.grid_columnconfigure(0, weight=1)

        self.sample_entry = ctk.CTkEntry(
            row, height=32, placeholder_text="Chưa chọn file mẫu âm thanh...",
            fg_color=theme.INPUT_BG, text_color=theme.INPUT_TEXT,
            placeholder_text_color=theme.INPUT_PLACEHOLDER,
            border_color=theme.SURFACE,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
        )
        self.sample_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            row, text="Chọn mẫu…", height=32, width=100,
            fg_color=theme.BUTTON_BG, hover_color=theme.BUTTON_HOVER,
            text_color=theme.TEXT,
            corner_radius=6, font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            command=self._choose_sample,
        ).grid(row=0, column=1)

        self.denoise_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            tab, text="Khử nhiễu file mẫu (nên bật nếu thu bằng điện thoại)",
            variable=self.denoise_var,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            text_color=theme.TEXT, hover_color=theme.ACCENT,
            fg_color=theme.ACCENT, corner_radius=4,
        ).grid(row=5, column=0, padx=12, pady=(0, 8), sticky="w")

        # ── Cam kết quyền sử dụng (bắt buộc) ──
        self.commit_var = ctk.BooleanVar(value=False)
        ctk.CTkLabel(
            tab, text=COMMITMENT_TEXT, text_color=theme.TEXT_DIM,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
            wraplength=460, justify="left",
        ).grid(row=6, column=0, padx=12, pady=(0, 2), sticky="w")
        self.commit_check = ctk.CTkCheckBox(
            tab, text="Tôi cam kết và chịu trách nhiệm về giọng nói này",
            variable=self.commit_var,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
            text_color=theme.TEXT, hover_color=theme.ACCENT,
            fg_color=theme.ACCENT, corner_radius=4,
        )
        self.commit_check.grid(row=7, column=0, padx=12, pady=(0, 8), sticky="w")

        self.create_btn = ctk.CTkButton(
            tab, text="🎙  Tạo giọng", height=42, fg_color=theme.SUCCESS,
            hover_color=theme.SUCCESS_HOVER, text_color="#ffffff", corner_radius=10,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE + 1, "bold"),
            command=self._start_create,
        )
        self.create_btn.grid(row=8, column=0, padx=12, pady=(4, 6), sticky="ew")

        self.create_progress = ctk.CTkProgressBar(tab, mode="indeterminate")
        self.create_progress.grid(row=9, column=0, padx=12, pady=(0, 4), sticky="ew")
        self.create_progress.stop()
        self.create_progress.grid_remove()

        self.create_status = ctk.CTkLabel(
            tab, text="", text_color=theme.TEXT_DIM,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1), wraplength=460,
            justify="left",
        )
        self.create_status.grid(row=10, column=0, padx=12, pady=(0, 12), sticky="w")

    # ── actions ──

    def _choose_file(self) -> None:
        from engine.vieneu_engine import VieneuTTS

        path = filedialog.askopenfilename(
            title="Chọn file giọng (.json)",
            filetypes=[("File giọng", "*.json"), ("Tất cả", "*.*")],
            parent=self,
        )
        if not path:
            return
        try:
            preview = VieneuTTS.read_portable_preview(path)
        except ValueError as exc:
            self._path = None
            self.path_entry.delete(0, "end")
            self.preview_label.configure(text="")
            self.error_label.configure(text=str(exc))
            self.import_btn.configure(state="disabled")
            return
        self._path = path
        self.path_entry.delete(0, "end")
        self.path_entry.insert(0, path)
        self.error_label.configure(text="")
        size_kb = max(preview["size"] // 1024, 1)
        desc = preview["description"] or "—"
        self.preview_label.configure(
            text=f"Tên: {preview['name']}   ·   {size_kb} KB\nMô tả: {desc}")
        self.import_btn.configure(state="normal")

    def _do_import(self) -> None:
        if self._path is None:
            return
        if self._on_import(self._path):
            self._close()

    # ── Tab 2: tạo giọng mới (chạy thread nền để không treo app) ──

    def _choose_sample(self) -> None:
        path = filedialog.askopenfilename(
            title="Chọn file mẫu âm thanh (5–30 giây)",
            filetypes=[("Âm thanh", "*.wav *.mp3 *.flac"),
                       ("Tất cả", "*.*")],
            parent=self,
        )
        if not path:
            return
        self._sample_path = path
        self.sample_entry.delete(0, "end")
        self.sample_entry.insert(0, path)
        self._create_set_status("")

    def _start_create(self) -> None:
        if self._creating:
            return
        name = self.create_name_entry.get().strip()
        if not name:
            self._create_set_status("Nhập tên giọng trước khi tạo.", theme.ERROR)
            return
        if not self._sample_path:
            self._create_set_status("Chọn file mẫu âm thanh trước khi tạo.",
                                    theme.ERROR)
            return
        if not self.commit_var.get():
            self._create_set_status(
                "Bạn cần tick cam kết quyền sử dụng giọng nói trước khi tạo.",
                theme.ERROR)
            return
        from engine.vieneu_engine import VieneuTTS

        if name in VieneuTTS.list_custom_voice_names():
            self._create_set_status(
                f"Đã có giọng '{name}'. Đặt tên khác hoặc xóa giọng cũ trước.",
                theme.ERROR)
            return
        self._creating = True
        self._create_result = None
        self.create_btn.configure(state="disabled", text="Đang tạo…")
        self.create_progress.grid()
        self.create_progress.start()
        self._create_set_status("Đang nạp model (lần đầu ~7 giây)...")
        threading.Thread(
            target=self._create_worker,
            args=(name, self.create_desc_entry.get().strip(),
                  self._sample_path, bool(self.denoise_var.get())),
            daemon=True,
        ).start()
        self.after(200, self._poll_create)

    def _create_worker(self, name: str, description: str,
                       sample: str, denoise: bool) -> None:
        tts = None
        owns_model = False
        try:
            from engine.vieneu_engine import VieneuTTS

            if self._tts_provider is not None:
                try:
                    tts = self._tts_provider()
                except Exception:
                    tts = None
            if tts is None:
                tts = VieneuTTS(low_memory=self._low_memory)
                owns_model = True
            tts.create_voice_from_sample(
                name, sample, description=description, denoise=denoise)
            self._create_result = (True, name)
        except Exception as exc:
            msg = str(exc)
            if ("speaker_encoder" in msg or "denoiser" in msg
                    or "Hub" in msg or "connection" in msg):
                msg += (" — Bộ cài thiếu file tạo giọng (speaker_encoder.onnx/"
                        "denoiser.onnx). Hãy chép lại thư mục 'models/' từ bộ cài gốc.")
            self._create_result = (False, msg)
        finally:
            # Chỉ đóng model do dialog tự nạp; model dùng chung do ModelManager giữ.
            if owns_model and tts is not None:
                tts.close()

    def _poll_create(self) -> None:
        if self._create_result is None:
            self.after(200, self._poll_create)
            return
        ok, payload = self._create_result
        self._creating = False
        self.create_progress.stop()
        self.create_progress.grid_remove()
        self.create_btn.configure(state="normal", text="Tạo giọng")
        if not ok:
            self._create_set_status(f"Lỗi: {payload}", theme.ERROR)
            return
        self._create_set_status(f"Đã tạo giọng '{payload}'.", theme.SUCCESS)
        if self._on_created is not None and self._on_created(payload):
            self._close()

    def _create_set_status(self, text: str,
                           color: str = theme.TEXT_DIM) -> None:
        self.create_status.configure(text=text, text_color=color)

    def _close(self) -> None:
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()
