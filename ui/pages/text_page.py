from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from ui import theme
from ui.components.sync_textbox import SyncTextbox
from ui.components.tag_bar import TagBar
from ui.shell.page import Page
from ui.ui_kit import Button, Card


class TextPage(Page):
    """Page “Đọc văn bản”: mở file, chọn giọng, test, soạn và chuyển đổi."""

    def __init__(self, master, ctx, **kwargs) -> None:
        super().__init__(master, ctx, page_id="text", title="Đọc văn bản",
                         subtitle="Chưa mở văn bản", **kwargs)

        self.open_btn = Button(self.header.actions, text="📁  Mở file",
                               variant="secondary", command=ctx._open_file)
        self.open_btn.pack(side="left", padx=(0, theme.SPACE_SM))
        self.export_btn = Button(self.header.actions, text="💾  Xuất file",
                                 variant="secondary", command=ctx._start_export)
        self.export_btn.pack(side="left", padx=(0, theme.SPACE_SM))
        self.convert_btn = Button(self.header.actions, text="⚡  Chuyển đổi",
                                  variant="primary", size="lg",
                                  command=ctx._start_convert)
        self.convert_btn.pack(side="left")

        # ── Hàng điều khiển: giọng đọc + test ──
        controls = Card(self.body, padding=theme.SPACE_MD, height=56)
        controls.grid(row=0, column=0, sticky="ew", pady=(0, theme.SPACE_SM))
        controls.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(
            controls, text="Giọng đọc",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2, "bold"),
            text_color=theme.TEXT_DIM,
        ).grid(row=0, column=0, padx=(theme.SPACE_SM, theme.SPACE_XS), sticky="w")

        self.voice_combo = ctk.CTkComboBox(
            controls, height=32, width=210, state="readonly",
            values=["(chưa có model)"], command=lambda _v: ctx._on_voice_change(_v),
            corner_radius=theme.RADIUS_SM,
            fg_color=theme.INPUT_BG, text_color=theme.INPUT_TEXT,
            border_color=theme.BORDER, border_width=1,
            button_color=theme.SURFACE_2, button_hover_color=theme.HOVER_BG,
            dropdown_fg_color=theme.SURFACE, dropdown_text_color=theme.TEXT,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            dropdown_font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
        )
        self.voice_combo.grid(row=0, column=1, sticky="w")

        self.add_voice_btn = Button(controls, text="＋ Thêm", variant="secondary",
                                    size="sm", command=ctx._open_voice_manager)
        self.add_voice_btn.grid(row=0, column=2, padx=theme.SPACE_SM, sticky="w")

        self.test_btn = Button(controls, text="🔊  Test", variant="secondary",
                               size="sm", command=ctx._test_voice)
        self.test_btn.grid(row=0, column=4, padx=(theme.SPACE_MD, theme.SPACE_XS),
                           sticky="e")

        self.test_entry = ctk.CTkEntry(
            controls, height=32, corner_radius=theme.RADIUS_SM,
            fg_color=theme.INPUT_BG, text_color=theme.INPUT_TEXT,
            placeholder_text_color=theme.INPUT_PLACEHOLDER,
            border_color=theme.BORDER, border_width=1,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            placeholder_text="Nhập câu test, Enter để lưu…",
        )
        from ui.config import load_test_text

        self.test_entry.insert(0, load_test_text())
        self.test_entry.grid(row=0, column=3, padx=(0, 0), sticky="ew")
        self.test_entry.bind("<Return>", lambda _e: self._save_test_text())

        # ── TagBar ──
        self.tag_bar = TagBar(
            self.body,
            on_insert=ctx._insert_tag,
            on_dictionary=ctx._open_dictionary,
            on_clean=ctx._clean_text,
        )
        self.tag_bar.grid(row=1, column=0, sticky="ew", pady=(0, theme.SPACE_XS))

        # ── Editor ──
        self.editor = SyncTextbox(self.body, on_text_changed=ctx._on_text_changed)
        self.editor.grid(row=2, column=0, sticky="nsew")
        self.body.grid_rowconfigure(0, weight=0)
        self.body.grid_rowconfigure(2, weight=1)

        top = self.winfo_toplevel()
        top.bind("<Control-Shift-D>", lambda _e: ctx._open_dictionary())
        top.bind("<Control-Shift-d>", lambda _e: ctx._open_dictionary())
        top.bind("<Control-Shift-K>", lambda _e: ctx._clean_text())
        top.bind("<Control-Shift-k>", lambda _e: ctx._clean_text())

    # ── facade tương thích TopBar cũ (mixin/probe) ──

    @property
    def source_label(self):
        return self.header.subtitle_label

    @property
    def status_label(self):
        return self.ctx.shell.toolbar.status_label

    @property
    def speed_combo(self):
        return self.ctx.shell.player_bar.speed_combo

    @property
    def license_label(self):
        return self.ctx.shell.sidebar.license_label

    @property
    def menus(self):
        return self.ctx.shell.toolbar.menus

    @property
    def menubar(self):
        return self.ctx.shell.toolbar

    def set_source_name(self, name: str | None) -> None:
        self.set_subtitle(name or "Chưa mở văn bản")

    def set_voices(self, names: list[str], selected: str | None = None) -> None:
        self.voice_combo.configure(values=names or ["(chưa có model)"])
        if names:
            self.voice_combo.set(selected or names[0])

    def get_selected_voice(self) -> str | None:
        return self.voice_combo.get() or None

    def get_speed(self) -> float:
        return self.ctx.shell.player_bar.get_speed()

    def set_status(self, message: str, color: str = theme.TEXT_DIM) -> None:
        self.ctx.shell.status(message, color)

    def set_license(self, text: str, color: str = theme.TEXT_DIM) -> None:
        self.ctx.shell.set_license(text, color)

    def set_export_locked(self, locked: bool) -> None:
        self.export_btn.configure(text="🔒  Xuất file" if locked else "💾  Xuất file")

    def set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.export_btn.configure(state=state)
        self.test_btn.configure(state=state)
        self.open_btn.configure(state=state)
        self.add_voice_btn.configure(state=state)
        if busy:
            self.convert_btn.configure(
                text="⏹  Dừng", fg_color=theme.DANGER,
                hover_color=theme.DANGER_HOVER, command=self.ctx._stop_convert,
            )
        else:
            self.convert_btn.configure(
                text="⚡  Chuyển đổi", fg_color=theme.PRIMARY,
                hover_color=theme.PRIMARY_HOVER, command=self.ctx._start_convert,
            )

    def get_test_text(self) -> str | None:
        from ui.config import load_test_text, save_test_text

        text = self.test_entry.get().strip()
        if text:
            save_test_text(text)
        return text or load_test_text()

    def _save_test_text(self) -> None:
        from ui.config import save_test_text

        text = self.test_entry.get().strip()
        if text:
            save_test_text(text)
            self.set_status("Đã lưu câu test.", theme.SUCCESS)
