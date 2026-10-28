from __future__ import annotations

import threading
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable

import customtkinter as ctk

from ui import theme
from ui.components.voice_import_dialog import ImportVoiceDialog


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
