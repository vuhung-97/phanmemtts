from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from ui import theme
from ui.ui_kit import PageHeader, ScrollArea


class Page(ctk.CTkFrame):
    """Base cho mọi page trong shell: header + vùng nội dung.

    ``body`` luôn là vùng cuộn dự phòng (``ScrollArea``): khi nội dung vừa khung
    thì lấp đầy như frame thường, khi cửa sổ quá nhỏ mới hiện thanh cuộn.
    Đặt ``scroll=False`` cho page không muốn cuộn toàn trang.
    """

    def __init__(self, master, ctx, page_id: str, title: str,
                 subtitle: str = "", scroll: bool = True, **kwargs) -> None:
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)
        self.ctx = ctx
        self.page_id = page_id
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.header = PageHeader(self, title=title, subtitle=subtitle)
        self.header.grid(row=0, column=0, sticky="ew", pady=(0, theme.SPACE_MD))

        if scroll:
            self.body = ScrollArea(self)
        else:
            self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=1, column=0, sticky="nsew")
        self.body.grid_columnconfigure(0, weight=1)

    # ── vòng đời ──

    def on_show(self) -> None:
        """Gọi khi page được hiển thị (refresh dữ liệu, focus)."""

    def on_hide(self) -> None:
        """Gọi khi rời page (dừng preview riêng, lưu nháp)."""

    def set_busy(self, busy: bool) -> None:
        """Khoá hành động riêng của page khi đang chạy."""

    # ── helper ──

    def add_action(self, widget) -> None:
        self.header.add_action(widget)

    def set_subtitle(self, text: str) -> None:
        self.header.set_subtitle(text)

    def refresh_layout(self) -> None:
        """Cập nhật lại vùng cuộn sau khi thay đổi widget cấp 1 trong body."""
        refresh = getattr(self.body, "refresh_layout", None)
        if refresh is not None:
            refresh()

    @property
    def status(self) -> Callable[[str, str], None]:
        return getattr(self.ctx, "status", lambda *_a, **_k: None)
