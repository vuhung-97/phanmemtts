from __future__ import annotations

from tkinter import filedialog, messagebox

import customtkinter as ctk

from ui import theme
from ui.config import load_enabled_voices, save_enabled_voices
from ui.shell.page import Page
from ui.ui_kit import Button, Card, SectionTitle


class VoicesPage(Page):
    """Trang Giọng đọc: bật/tắt giọng, nhập / tạo / xuất / xoá giọng tùy chỉnh."""

    def __init__(self, master, ctx, **kwargs) -> None:
        super().__init__(master, ctx, page_id="voices", title="Giọng đọc",
                         subtitle="Chọn giọng hiển thị, nhập hoặc tạo giọng mới",
                         **kwargs)
        self._checkboxes: dict[str, ctk.CTkCheckBox] = {}
        self._models: list = []

        Button(self.header.actions, text="＋  Thêm giọng mới", variant="primary",
               command=self._open_import).pack(side="left", padx=(0, theme.SPACE_SM))
        self.save_btn = Button(self.header.actions, text="💾  Lưu lựa chọn",
                               variant="secondary", command=self._save)
        self.save_btn.pack(side="left")

        self.body.grid_rowconfigure(0, weight=0)
        self.body.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(self.body, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", pady=(0, theme.SPACE_SM))
        top.grid_columnconfigure(1, weight=1)
        SectionTitle(top, "Danh sách giọng").grid(row=0, column=0, sticky="w")
        self.count_label = ctk.CTkLabel(
            top, text="", text_color=theme.TEXT_DIM, anchor="e",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
        )
        self.count_label.grid(row=0, column=1, padx=theme.SPACE_SM, sticky="e")
        Button(top, text="Chọn tất cả", variant="ghost", size="sm",
               command=self._select_all).grid(row=0, column=2, padx=(0, 4))
        Button(top, text="Bỏ chọn", variant="ghost", size="sm",
               command=self._deselect_all).grid(row=0, column=3)

        card = Card(self.body, padding=theme.SPACE_MD)
        card.grid(row=1, column=0, sticky="nsew")
        card.grid_rowconfigure(0, weight=1)
        card.grid_columnconfigure(0, weight=1)
        self._list = ctk.CTkScrollableFrame(card, fg_color=theme.SURFACE)
        self._list.grid(row=0, column=0, sticky="nsew")
        self._list.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            self.body, text="", anchor="w", text_color=theme.TEXT_DIM,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
        )
        self.status_label.grid(row=2, column=0, pady=(theme.SPACE_XS, 0), sticky="w")

    # ── dựng danh sách ──

    def on_show(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        enabled = load_enabled_voices()
        self._models = self.ctx._scan_models() or []
        if enabled is None:
            enabled = {m.model_id for m in self._models}
        self._render(enabled)

    def _render(self, enabled: set[str]) -> None:
        from engine.vieneu_engine import VieneuTTS

        customs = set(VieneuTTS.list_custom_voice_names())
        for child in self._list.winfo_children():
            child.destroy()
        self._checkboxes = {}

        for index, model in enumerate(self._models):
            is_custom = (model.model_id.startswith("vieneu:")
                         and model.model_id.split(":", 1)[-1] in customs)
            row = ctk.CTkFrame(self._list, fg_color="transparent")
            row.grid(row=index, column=0, padx=theme.SPACE_XS, pady=1, sticky="ew")
            row.grid_columnconfigure(0, weight=1)

            var = ctk.BooleanVar(value=model.model_id in enabled)
            checkbox = ctk.CTkCheckBox(
                row, text=model.display_name, variable=var,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
                text_color=theme.TEXT, hover_color=theme.PRIMARY,
                fg_color=theme.PRIMARY, corner_radius=4,
            )
            checkbox.grid(row=0, column=0, sticky="w")
            self._checkboxes[model.model_id] = checkbox

            if is_custom:
                voice_name = model.model_id.split(":", 1)[-1]
                Button(row, text="⬇", variant="ghost", size="sm", width=30,
                       command=lambda n=voice_name: self._export_voice(n)).grid(
                    row=0, column=1, padx=(theme.SPACE_XS, 2))
                Button(row, text="🗑", variant="ghost", size="sm", width=30,
                       command=lambda n=voice_name: self._delete_voice(n)).grid(
                    row=0, column=2, padx=(0, 2))

        self._update_count()
        self._set_status("")

    def _update_count(self) -> None:
        total = len(self._checkboxes)
        checked = len(self._checked())
        self.count_label.configure(text=f"{checked}/{total} giọng đang bật")

    def _checked(self) -> set[str]:
        return {mid for mid, cb in self._checkboxes.items() if cb.get()}

    def _select_all(self) -> None:
        for checkbox in self._checkboxes.values():
            checkbox.select()
        self._update_count()

    def _deselect_all(self) -> None:
        for checkbox in self._checkboxes.values():
            checkbox.deselect()
        self._update_count()

    def _save(self) -> None:
        if not self._checked():
            self._set_status("Phải bật ít nhất một giọng.", theme.ERROR)
            return
        save_enabled_voices(self._checked())
        self.ctx._scan_models()
        self._set_status("Đã lưu lựa chọn giọng.", theme.SUCCESS)
        self.ctx.shell.status("Đã lưu lựa chọn giọng.", theme.SUCCESS)

    # ── thêm / nhập / xuất / xoá ──

    def _open_import(self) -> None:
        from ui.components.voice_import_dialog import ImportVoiceDialog

        ImportVoiceDialog(self, on_import=self._import_portable,
                          on_created=self._voice_created)

    def _voice_created(self, name: str) -> bool:
        checked = self._checked() | {f"vieneu:{name}"}
        save_enabled_voices(checked)
        self.ctx._model_manager.unload_if(f"vieneu:{name}")
        self._rescan(keep=checked)
        self._set_status(f"Đã tạo giọng '{name}'.", theme.SUCCESS)
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
                    f"Đã có giọng tùy chỉnh tên '{name}'. Ghi đè không?",
                    parent=self):
                return False
        try:
            VieneuTTS.import_voice_file(path)
        except ValueError as exc:
            self._set_status(f"Lỗi: {exc}", theme.ERROR)
            return False
        checked = self._checked() | {f"vieneu:{name}"}
        save_enabled_voices(checked)
        self.ctx._model_manager.unload_if(f"vieneu:{name}")
        self._rescan(keep=checked)
        self._set_status(f"Đã nhập giọng '{name}'.", theme.SUCCESS)
        return True

    def _rescan(self, keep: set[str]) -> None:
        self._models = self.ctx._scan_models() or []
        self._render(keep)

    def _export_voice(self, name: str) -> None:
        from engine.vieneu_engine import VieneuTTS

        path = filedialog.asksaveasfilename(
            title="Xuất file giọng", initialfile=f"{name}.json",
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
                "Xóa giọng?",
                f"Xóa giọng tùy chỉnh '{name}'?\n"
                f"(Không ảnh hưởng file mẫu đã nhập trước đó)",
                parent=self):
            return
        VieneuTTS.delete_custom_voice(name)
        mid = f"vieneu:{name}"
        checked = self._checked() - {mid}
        save_enabled_voices(checked)
        self.ctx._model_manager.unload_if(mid)
        self._rescan(keep=checked)
        self._set_status(f"Đã xóa giọng '{name}'.", theme.SUCCESS)

    def _set_status(self, text: str, color: str = theme.TEXT_DIM) -> None:
        self.status_label.configure(text=text, text_color=color)
