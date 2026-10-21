from __future__ import annotations

import threading
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable

import customtkinter as ctk

from ui import theme


class VoiceManagerDialog(ctk.CTkToplevel):
    """Dialog modal: checklist giọng đọc + thêm/xuất/xóa giọng tùy chỉnh + lưu/huỷ."""

    def __init__(self, master, all_models: list, enabled_ids: set[str],
                 on_save: Callable[[set[str]], None],
                 get_models: Callable[[], list] | None = None,
                 on_voice_changed: Callable[[str], None] | None = None,
                 ) -> None:
        super().__init__(master)
        self.title("Quản lý giọng đọc")
        self.geometry("520x640")
        self.minsize(440, 500)
        self.configure(fg_color=theme.DIALOG_BG)
        self.transient(master)
        self.grab_set()

        self._all_models = all_models
        self._on_save = on_save
        self._get_models = get_models   # rescan + trả về list mới (None -> giữ list cũ)
        self._on_voice_changed = on_voice_changed  # (name) -> app hủy nạp nếu đang dùng
        self._checkboxes: dict[str, ctk.CTkCheckBox] = {}
        self._scroll = None

        self._build_ui(enabled_ids)
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Escape>", lambda _: self._cancel())

    # ── UI ──

    def _build_ui(self, enabled_ids: set[str]) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Tiêu đề
        ctk.CTkLabel(
            self, text="Chọn giọng hiển thị trong combobox",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE + 2, "bold"),
            text_color=theme.TEXT,
        ).grid(row=0, column=0, padx=20, pady=(16, 4), sticky="w")

        # Danh sách checkbox (scroll)
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color=theme.SURFACE, corner_radius=8,
        )
        self._scroll.grid(row=1, column=0, padx=20, pady=8, sticky="nsew")
        self._scroll.grid_columnconfigure(0, weight=1)
        self._rebuild_list(enabled_ids)

        # Hàng nút: Tất cả / Bỏ chọn / Thêm giọng mới
        mid = ctk.CTkFrame(self, fg_color="transparent")
        mid.grid(row=2, column=0, padx=20, pady=(0, 4), sticky="ew")
        mid.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(
            mid, text="☑ Tất cả", height=30,
            fg_color="transparent", border_width=1, border_color=theme.SIDEBAR_DIVIDER,
            text_color=theme.TEXT, hover_color=theme.SURFACE, corner_radius=6,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            command=self._select_all,
        ).grid(row=0, column=0, padx=(0, 4), sticky="ew")

        ctk.CTkButton(
            mid, text="□ Bỏ chọn", height=30,
            fg_color="transparent", border_width=1, border_color=theme.SIDEBAR_DIVIDER,
            text_color=theme.TEXT, hover_color=theme.SURFACE, corner_radius=6,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            command=self._deselect_all,
        ).grid(row=0, column=1, padx=4, sticky="ew")

        ctk.CTkButton(
            mid, text="＋ Thêm giọng mới", height=30,
            fg_color="transparent", border_width=1, border_color=theme.ACCENT,
            text_color=theme.ACCENT, hover_color=theme.SURFACE, corner_radius=6,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
            command=self._open_import_dialog,
        ).grid(row=0, column=2, padx=(4, 0), sticky="ew")

        # Status chung (thêm/xuất/xóa)
        self.status_label = ctk.CTkLabel(
            self, text="",
            text_color=theme.TEXT_DIM,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1), wraplength=480,
            justify="left",
        )
        self.status_label.grid(row=3, column=0, padx=20, pady=(0, 4), sticky="w")

        # Hàng nút cuối: Lưu / Huỷ
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=4, column=0, padx=20, pady=(4, 16), sticky="ew")
        bottom.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            bottom, text="💾 Lưu", height=36, fg_color=theme.DARK_BUTTON_BG,
            hover_color=theme.DARK_BUTTON_HOVER, text_color=theme.DARK_BUTTON_TEXT,
            corner_radius=8,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
            command=self._save,
        ).grid(row=0, column=0, padx=(0, 4), sticky="ew")

        ctk.CTkButton(
            bottom, text="✕ Huỷ", height=36,
            fg_color="transparent", border_width=1, border_color=theme.SIDEBAR_DIVIDER,
            text_color=theme.TEXT, hover_color=theme.SURFACE, corner_radius=8,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            command=self._cancel,
        ).grid(row=0, column=1, padx=(4, 0), sticky="ew")

    def _rebuild_list(self, checked_ids: set[str]) -> None:
        """Vẽ lại checklist theo checked_ids (giữ cuộn hiện tại)."""
        from engine.vieneu_engine import VieneuTTS

        for child in self._scroll.winfo_children():
            child.destroy()
        self._checkboxes = {}

        customs = set(VieneuTTS.list_custom_voice_names())
        for i, model in enumerate(self._all_models):
            is_custom = (model.model_id.startswith("vieneu:")
                         and model.model_id.split(":", 1)[-1] in customs)
            row = ctk.CTkFrame(self._scroll, fg_color="transparent")
            row.grid(row=i, column=0, padx=6, pady=2, sticky="ew")
            row.grid_columnconfigure(0, weight=1)

            var = ctk.BooleanVar(value=model.model_id in checked_ids)
            cb = ctk.CTkCheckBox(
                row, text=model.display_name, variable=var,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE),
                text_color=theme.TEXT, hover_color=theme.ACCENT,
                fg_color=theme.ACCENT, corner_radius=4,
            )
            cb.grid(row=0, column=0, sticky="w")
            self._checkboxes[model.model_id] = cb

            if is_custom:
                voice_name = model.model_id.split(":", 1)[-1]
                ctk.CTkButton(
                    row, text="⬇", width=32, height=24,
                    fg_color="transparent", border_width=1,
                    border_color=theme.SIDEBAR_DIVIDER, text_color=theme.TEXT_DIM,
                    hover_color=theme.SURFACE, corner_radius=4,
                    font=(theme.FONT_FAMILY, theme.FONT_SIZE),
                    command=lambda n=voice_name: self._export_voice(n),
                ).grid(row=0, column=1, padx=(4, 2))
                ctk.CTkButton(
                    row, text="🗑", width=32, height=24,
                    fg_color="transparent", border_width=1,
                    border_color=theme.ERROR, text_color=theme.ERROR,
                    hover_color=theme.SURFACE, corner_radius=4,
                    font=(theme.FONT_FAMILY, theme.FONT_SIZE),
                    command=lambda n=voice_name: self._delete_voice(n),
                ).grid(row=0, column=2, padx=(0, 2))

    # ── actions ──

    def _select_all(self) -> None:
        for cb in self._checkboxes.values():
            cb.select()

    def _deselect_all(self) -> None:
        for cb in self._checkboxes.values():
            cb.deselect()

    def _collect_checked(self) -> set[str]:
        return {
            mid for mid, cb in self._checkboxes.items()
            if cb.get()
        }

    def _save(self) -> None:
        self._on_save(self._collect_checked())
        self.destroy()

    def _cancel(self) -> None:
        self.destroy()

    def _set_status(self, text: str, color: str = theme.TEXT_DIM) -> None:
        self.status_label.configure(text=text, text_color=color)

    def _refresh_models(self, add: set[str] | None = None,
                        remove: set[str] | None = None) -> None:
        """Rescan danh sách giọng (nếu có get_models) + vẽ lại checklist."""
        if self._get_models is None:
            return
        checked = self._collect_checked() | (add or set())
        checked -= remove or set()
        old_ids = {m.model_id for m in self._all_models}
        self._all_models = self._get_models()
        existing = {m.model_id for m in self._all_models}
        # Giọng mới thêm -> tick sẵn; các mục khác giữ nguyên lựa chọn
        checked = (checked & existing) | (existing - old_ids)
        self._rebuild_list(checked)

    # ── Thêm (nhập file giọng) ──

    def _open_import_dialog(self) -> None:
        ImportVoiceDialog(self, on_import=self._import_portable,
                          on_created=self._voice_created)

    def _voice_created(self, name: str) -> bool:
        """Giọng vừa tạo từ file mẫu: tick sẵn + refresh như luồng nhập file."""
        checked = self._collect_checked() | {f"vieneu:{name}"}
        self._on_save(checked)
        if self._on_voice_changed:
            self._on_voice_changed(name)
        self._refresh_models()
        self._set_status(f"Đã tạo giọng '{name}'. Bấm Lưu để giữ lựa chọn.",
                         theme.SUCCESS)
        return True

    def _import_portable(self, path: str) -> bool:
        from engine.vieneu_engine import VieneuTTS

        try:
            preview = VieneuTTS.read_portable_preview(path)
        except ValueError as exc:
            self._set_status(f"Lỗi: {exc}", theme.ERROR)
            return False

        name = preview["name"]
        if name in VieneuTTS.list_custom_voice_names():
            if not messagebox.askyesno(
                    "Ghi đè giọng?",
                    f"Đã có giọng tùy chỉnh tên '{name}'. Ghi đè không?"):
                return False
        try:
            VieneuTTS.import_voice_file(path)
        except ValueError as exc:
            self._set_status(f"Lỗi: {exc}", theme.ERROR)
            return False

        # Lưu ngay để giọng hiện ở sidebar (không phải bấm Lưu mới thấy)
        checked = self._collect_checked() | {f"vieneu:{name}"}
        self._on_save(checked)
        if self._on_voice_changed:
            self._on_voice_changed(name)  # ghi đè giọng đang nạp -> app tải lại
        self._refresh_models()
        self._set_status(f"Đã nhập giọng '{name}'. Bấm Lưu để giữ lựa chọn.",
                         theme.SUCCESS)
        return True

    # ── Xuất / xóa giọng tùy chỉnh ──

    def _export_voice(self, name: str) -> None:
        from engine.vieneu_engine import VieneuTTS

        path = filedialog.asksaveasfilename(
            title="Xuất file giọng",
            initialfile=f"{name}.json",
            defaultextension=".json",
            filetypes=[("File giọng", "*.json"), ("Tất cả", "*.*")],
            parent=self,
        )
        if not path:
            return
        try:
            VieneuTTS.export_voice_file(name, path)
            self._set_status(f"Đã xuất '{name}' → {path}", theme.SUCCESS)
        except (ValueError, OSError) as exc:
            self._set_status(f"Lỗi xuất file: {exc}", theme.ERROR)

    def _delete_voice(self, name: str) -> None:
        from engine.vieneu_engine import VieneuTTS

        if not messagebox.askyesno(
                "Xóa giọng?", f"Xóa giọng tùy chỉnh '{name}'?\n"
                              f"(Không ảnh hưởng file mẫu đã nhập trước đó)"):
            return
        VieneuTTS.delete_custom_voice(name)
        mid = f"vieneu:{name}"
        checked = self._collect_checked() - {mid}
        self._on_save(checked)
        if self._on_voice_changed:
            self._on_voice_changed(name)
        self._refresh_models(remove={mid})
        self._set_status(f"Đã xóa giọng '{name}'.", theme.SUCCESS)


class ImportVoiceDialog(ctk.CTkToplevel):
    """Hộp thoại 2 tab: nhập file giọng có sẵn (.json) / tạo giọng mới từ mẫu."""

    def __init__(self, master, on_import: Callable[[str], bool],
                 on_created: Callable[[str], bool] | None = None) -> None:
        super().__init__(master)
        self.title("Thêm giọng mới")
        self.geometry("540x640")
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

    # ── Tab 1: nhập file giọng có sẵn (giữ nguyên luồng cũ) ──

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
                 "B3: bấm “Tạo giọng” và chờ ~10 giây (lần đầu cần mạng để tải model).",
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

        self.create_btn = ctk.CTkButton(
            tab, text="🎙  Tạo giọng", height=42, fg_color=theme.SUCCESS,
            hover_color=theme.SUCCESS_HOVER, text_color="#ffffff", corner_radius=10,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE + 1, "bold"),
            command=self._start_create,
        )
        self.create_btn.grid(row=6, column=0, padx=12, pady=(4, 6), sticky="ew")

        self.create_progress = ctk.CTkProgressBar(tab, mode="indeterminate")
        self.create_progress.grid(row=7, column=0, padx=12, pady=(0, 4), sticky="ew")
        self.create_progress.stop()
        self.create_progress.grid_remove()

        self.create_status = ctk.CTkLabel(
            tab, text="", text_color=theme.TEXT_DIM,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1), wraplength=460,
            justify="left",
        )
        self.create_status.grid(row=8, column=0, padx=12, pady=(0, 12), sticky="w")

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
        try:
            from engine.vieneu_engine import VieneuTTS

            tts = VieneuTTS()
            tts.create_voice_from_sample(
                name, sample, description=description, denoise=denoise)
            self._create_result = (True, name)
        except Exception as exc:
            msg = str(exc)
            if ("speaker_encoder" in msg or "Hub" in msg
                    or "connection" in msg):
                msg += " — Gợi ý: chạy 'python download_model.py' rồi tạo lại."
            self._create_result = (False, msg)

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
