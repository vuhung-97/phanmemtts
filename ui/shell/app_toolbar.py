from __future__ import annotations

import os
from tkinter import Menu
from typing import Callable

import customtkinter as ctk

from core.paths import data_dir
from ui import theme
from ui.ui_kit import Button

_TOOLBAR_BG = theme.SURFACE


class AppToolbar(ctk.CTkFrame):
    """Thanh công cụ: menu Tệp / Trợ giúp + trạng thái toàn cục."""

    def __init__(
        self,
        master,
        on_open_file: Callable[[], None] | None = None,
        on_help: Callable[[], None] | None = None,
        on_terms: Callable[[], None] | None = None,
        on_license: Callable[[], None] | None = None,
        on_about: Callable[[], None] | None = None,
        on_close: Callable[[], None] | None = None,
        **kwargs,
    ) -> None:
        kwargs.setdefault("fg_color", _TOOLBAR_BG)
        kwargs.setdefault("corner_radius", 0)
        kwargs.setdefault("height", theme.TOOLBAR_HEIGHT)
        super().__init__(master, **kwargs)
        self.grid_propagate(False)
        self.grid_columnconfigure(2, weight=1)

        self._on_open_file = on_open_file
        self._on_help = on_help
        self._on_terms = on_terms
        self._on_license = on_license
        self._on_about = on_about
        self._on_close = on_close

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=0, column=0, padx=(theme.SPACE_MD, 0), sticky="w")
        self._menu_buttons: dict[str, ctk.CTkButton] = {}
        self.menus: dict[str, Menu] = {}

        for key, label in (("file", "Tệp"), ("help", "Trợ giúp")):
            button = Button(
                bar, text=label, variant="ghost", size="sm", width=64,
                command=lambda k=key: self._popup_menu(k),
            )
            button.pack(side="left", padx=(0, 2))
            self._menu_buttons[key] = button

        self._build_file_menu()
        self._build_help_menu()

        divider = ctk.CTkFrame(self, width=1, height=1, fg_color=theme.BORDER)
        divider.grid(row=0, column=1, padx=theme.SPACE_MD, pady=10, sticky="ns")

        status = ctk.CTkFrame(self, fg_color="transparent")
        status.grid(row=0, column=2, padx=theme.SPACE_SM, sticky="w")
        self.status_dot = ctk.CTkLabel(
            status, text="●", text_color=theme.SUCCESS,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
        )
        self.status_dot.pack(side="left")
        self.status_label = ctk.CTkLabel(
            status, text="Sẵn sàng", anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            text_color=theme.TEXT_DIM,
        )
        self.status_label.pack(side="left", padx=(theme.SPACE_XS, 0))

        self.voices_label = ctk.CTkLabel(
            self, text="", anchor="e",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
            text_color=theme.TEXT_DIM,
        )
        self.voices_label.grid(row=0, column=3, padx=(0, theme.SPACE_XL))

        self._bind_shortcuts()

    # ── menu ──

    def _make_menu(self) -> Menu:
        return Menu(
            self, tearoff=0, bd=0, relief="flat",
            bg=theme.SURFACE, fg=theme.TEXT,
            activebackground=theme.PRIMARY_SOFT, activeforeground=theme.PRIMARY,
            disabledforeground=theme.INPUT_PLACEHOLDER,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
        )

    def _build_file_menu(self) -> None:
        menu = self._make_menu()
        if self._on_open_file is not None:
            menu.add_command(label="Mở văn bản…", accelerator="Ctrl+O",
                             command=self._on_open_file)
        menu.add_command(label="Mở thư mục dữ liệu…", command=self._open_data_dir)
        menu.add_separator()
        menu.add_command(label="Thoát", accelerator="Alt+F4",
                         command=self._on_close)
        self.menus["file"] = menu

    def _build_help_menu(self) -> None:
        menu = self._make_menu()
        if self._on_help is not None:
            menu.add_command(label="Hướng dẫn sử dụng", command=self._on_help)
        if self._on_terms is not None:
            menu.add_command(label="Điều khoản sử dụng", command=self._on_terms)
        if self._on_license is not None:
            menu.add_command(label="Thông tin bản quyền",
                             accelerator="Ctrl+Shift+L",
                             command=self._on_license)
        menu.add_separator()
        if self._on_about is not None:
            menu.add_command(label="Giới thiệu", command=self._on_about)
        self.menus["help"] = menu

    def _popup_menu(self, key: str) -> None:
        menu = self.menus.get(key)
        button = self._menu_buttons.get(key)
        if menu is None or button is None:
            return
        try:
            menu.tk_popup(button.winfo_rootx(),
                          button.winfo_rooty() + button.winfo_height())
        finally:
            menu.grab_release()

    def _bind_shortcuts(self) -> None:
        top = self.winfo_toplevel()
        if self._on_open_file is not None:
            top.bind("<Control-o>", lambda _e: self._on_open_file())
        if self._on_license is not None:
            top.bind("<Control-Shift-L>", lambda _e: self._on_license())
            top.bind("<Control-Shift-l>", lambda _e: self._on_license())
        top.bind("<Alt-f>", lambda _e: self._open_menu("file"))
        top.bind("<Alt-t>", lambda _e: self._open_menu("help"))

    def _open_menu(self, key: str) -> None:
        self.after(1, lambda: self._popup_menu(key))

    def _open_data_dir(self) -> None:
        path = data_dir()
        try:
            if os.name == "nt":
                os.startfile(str(path))  # type: ignore[attr-defined]
            else:
                import subprocess
                subprocess.Popen(["xdg-open", str(path)])
        except Exception:
            self.set_status(f"Thư mục dữ liệu: {path}", theme.TEXT_DIM)

    # ── API ──

    def set_status(self, message: str, color: str = theme.TEXT_DIM) -> None:
        self.status_label.configure(text=message, text_color=color)
        tone = theme.SUCCESS
        if color == theme.ERROR:
            tone = theme.ERROR
        elif color in (theme.WARNING, "#b7791f"):
            tone = theme.WARNING
        self.status_dot.configure(text_color=tone)

    def set_voices(self, count: int, total: int | None = None) -> None:
        if total is None:
            text = f"{count} giọng"
        else:
            text = f"{count}/{total} giọng"
        self.voices_label.configure(text=text)

    def set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        for button in self._menu_buttons.values():
            button.configure(state=state)
