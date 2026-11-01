from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from ui import theme
from ui.shell.app_header import AppHeader
from ui.shell.app_toolbar import AppToolbar
from ui.shell.nav_sidebar import NavSidebar
from ui.shell.page import Page
from ui.shell.player_bar import PlayerBar


class AppShell(ctk.CTkFrame):
    """Khung ứng dụng SaaS: header + toolbar + sidebar + nội dung + player."""

    def __init__(
        self,
        master,
        app_name: str,
        version: str,
        toolbar_callbacks: dict[str, Callable] | None = None,
        on_navigate: Callable[[str], None] | None = None,
        player_callbacks: dict[str, Callable] | None = None,
        **kwargs,
    ) -> None:
        kwargs.setdefault("fg_color", theme.BG)
        kwargs.setdefault("corner_radius", 0)
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.header = AppHeader(self, app_name=app_name, version=version)
        self.header.grid(row=0, column=0, sticky="ew")

        callbacks = toolbar_callbacks or {}
        self.toolbar = AppToolbar(
            self,
            on_open_file=callbacks.get("open_file"),
            on_help=callbacks.get("help"),
            on_terms=callbacks.get("terms"),
            on_license=callbacks.get("license"),
            on_about=callbacks.get("about"),
            on_close=callbacks.get("close"),
        )
        self.toolbar.grid(row=1, column=0, sticky="ew")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=2, column=0, sticky="nsew")
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        self.sidebar = NavSidebar(
            body, on_navigate=on_navigate or (lambda _p: None))
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)

        divider = ctk.CTkFrame(body, width=1, fg_color=theme.BORDER)
        divider.grid(row=0, column=0, sticky="nse")

        self.content = ctk.CTkFrame(body, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew",
                          padx=(theme.SPACE_XL, theme.SPACE_XL),
                          pady=(theme.SPACE_MD, theme.SPACE_SM))
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        player = player_callbacks or {}
        self.player_bar = PlayerBar(
            self,
            on_toggle=player.get("toggle", lambda: None),
            on_seek=player.get("seek", lambda _s: None),
            on_prev_sentence=player.get("prev", lambda: None),
            on_next_sentence=player.get("next", lambda: None),
            on_speed_change=player.get("speed", lambda _v: None),
        )
        self.player_bar.grid(row=3, column=0, sticky="ew")

        self._pages: dict[str, Page] = {}
        self._current: Page | None = None
        self._busy = False

        # Ctrl+1…9 chuyển nhanh theo thứ tự sidebar
        from ui.shell.nav_sidebar import NAV_MAIN, NAV_TOOLS

        top = self.winfo_toplevel()
        for index, (page_id, _icon, _label) in enumerate(NAV_MAIN + NAV_TOOLS, 1):
            top.bind(
                f"<Control-Key-{index}>",
                lambda _e, pid=page_id: (on_navigate or (lambda _p: None))(pid),
            )

    # ── router ──

    def register(self, page: Page) -> None:
        self._pages[page.page_id] = page
        page.grid(row=0, column=0, sticky="nsew")
        page.grid_remove()

    def has_page(self, page_id: str) -> bool:
        return page_id in self._pages

    def show(self, page_id: str) -> bool:
        page = self._pages.get(page_id)
        if page is None:
            return False
        if self._current is page:
            self.sidebar.set_active(page_id)
            return True
        if self._current is not None:
            self._current.on_hide()
            self._current.grid_remove()
        page.grid()
        self._current = page
        self.sidebar.set_active(page_id)
        page.on_show()
        return True

    @property
    def current_page(self) -> Page | None:
        return self._current

    # ── trạng thái chung ──

    def status(self, text: str, color: str = theme.TEXT_DIM) -> None:
        self.toolbar.set_status(text, color)

    def set_license(self, text: str, color: str = theme.TEXT_DIM) -> None:
        self.sidebar.set_license(text, color)

    def set_voices(self, count: int, total: int | None = None) -> None:
        self.toolbar.set_voices(count, total)

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.toolbar.set_busy(busy)
        self.sidebar.set_busy(busy)
        if self._current is not None:
            self._current.set_busy(busy)

    @property
    def busy(self) -> bool:
        return self._busy
