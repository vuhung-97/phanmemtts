from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from core.licensing import edition
from ui import theme
from ui.ui_kit import Button, Tooltip

NAV_MAIN: tuple[tuple[str, str, str], ...] = (
    ("text", "📖", "Đọc văn bản"),
    ("dialogue", "🎭", "Hội thoại"),
    ("merge", "🎵", "Ghép nhạc"),
    ("batch", "📦", "Hàng loạt"),
    ("history", "🕘", "Lịch sử"),
)

NAV_TOOLS: tuple[tuple[str, str, str], ...] = (
    ("dictionary", "🔤", "Từ điển"),
    ("voices", "🎙", "Giọng đọc"),
    ("settings", "⚙", "Cài đặt"),
    ("license", "🔑", "Bản quyền"),
)


def nav_items() -> tuple[tuple[str, str, str], ...]:
    """Mục sidebar hiển thị theo chế độ phát hành (full ẩn Bản quyền)."""
    tools = tuple(item for item in NAV_TOOLS
                  if item[0] != "license" or edition.license_visible())
    return NAV_MAIN + tools


class NavSidebar(ctk.CTkFrame):
    """Sidebar chức năng: nhóm chính + nhóm công cụ + chân bản quyền."""

    def __init__(self, master, on_navigate: Callable[[str], None],
                 **kwargs) -> None:
        kwargs.setdefault("fg_color", theme.SIDEBAR_BG)
        kwargs.setdefault("corner_radius", 0)
        kwargs.setdefault("width", theme.SIDEBAR_WIDTH)
        super().__init__(master, **kwargs)
        self.grid_propagate(False)
        self.grid_columnconfigure(0, weight=1)

        self._on_navigate = on_navigate
        self._active: str | None = "text"
        self._collapsed = False
        self._busy = False
        self._license_text = ""
        self._license_color = theme.TEXT_DIM
        self._tooltips: list[Tooltip] = []

        self._body = ctk.CTkFrame(self, fg_color="transparent")
        self._body.grid(row=0, column=0, sticky="nsew", padx=theme.SPACE_SM,
                        pady=theme.SPACE_SM)
        self.grid_rowconfigure(0, weight=1)

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=1, column=0, sticky="ew", padx=theme.SPACE_SM,
                    pady=(0, theme.SPACE_SM))
        footer.grid_columnconfigure(0, weight=1)

        self.license_label = ctk.CTkLabel(
            footer, text="", anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
            text_color=theme.TEXT_DIM, cursor="hand2",
        )
        self.license_label.grid(row=0, column=0, sticky="w", padx=theme.SPACE_XS)
        if edition.license_visible():
            self.license_label.bind("<Button-1>",
                                    lambda _e: self._navigate("license"))
        else:
            self.license_label.grid_remove()

        self.collapse_btn = Button(
            footer, text="«", variant="ghost", size="sm", width=28,
            command=self.toggle_collapsed,
        )
        self.collapse_btn.grid(row=0, column=1, sticky="e")

        self._render()

    # ── render ──

    def _render(self) -> None:
        for child in self._body.winfo_children():
            child.destroy()
        self._tooltips.clear()

        items = nav_items()
        row = 0
        for page_id, icon, label in items[:len(NAV_MAIN)]:
            self._item(row, page_id, icon, label)
            row += 1

        if not self._collapsed:
            ctk.CTkLabel(
                self._body, text="CÔNG CỤ", anchor="w",
                font=(theme.FONT_FAMILY, 10, "bold"),
                text_color=theme.TEXT_DIM,
            ).grid(row=row, column=0, padx=theme.SPACE_SM,
                   pady=(theme.SPACE_LG, theme.SPACE_XS), sticky="w")
            row += 1
        else:
            ctk.CTkFrame(self._body, height=1, fg_color=theme.BORDER).grid(
                row=row, column=0, padx=theme.SPACE_SM,
                pady=(theme.SPACE_MD, theme.SPACE_SM), sticky="ew")
            row += 1

        for page_id, icon, label in items[len(NAV_MAIN):]:
            self._item(row, page_id, icon, label)
            row += 1

        self._body.grid_columnconfigure(0, weight=1)
        self.collapse_btn.configure(text="»" if self._collapsed else "«")
        self.configure(width=theme.SIDEBAR_COLLAPSED if self._collapsed
                       else theme.SIDEBAR_WIDTH)
        self._refresh_license()

    def _item(self, row: int, page_id: str, icon: str, label: str) -> None:
        active = page_id == self._active
        text = icon if self._collapsed else f"{icon}   {label}"
        button = ctk.CTkButton(
            self._body, text=text, anchor="w" if not self._collapsed else "center",
            height=34, width=0 if not self._collapsed else 34,
            corner_radius=theme.RADIUS_SM,
            fg_color=theme.PRIMARY_SOFT if active else "transparent",
            hover_color="#E8EEFC",
            text_color=theme.PRIMARY if active else theme.TEXT_DIM,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold" if active else "normal"),
            command=lambda pid=page_id: self._navigate(pid),
        )
        button.grid(row=row, column=0, sticky="ew" if not self._collapsed else "",
                    padx=(theme.SPACE_XS, theme.SPACE_XS),
                    pady=1)
        if self._collapsed:
            self._tooltips.append(Tooltip(button, label))

    def _navigate(self, page_id: str) -> None:
        if page_id == "license" and not edition.license_visible():
            return
        if self._busy and page_id != "history":
            return
        self.set_active(page_id)
        self._on_navigate(page_id)

    # ── API ──

    def set_active(self, page_id: str | None) -> None:
        self._active = page_id
        self._render()

    def set_license(self, text: str, color: str = theme.TEXT_DIM) -> None:
        self._license_text = text
        self._license_color = color
        self._refresh_license()

    def _refresh_license(self) -> None:
        if not edition.license_visible():
            return
        if not self._license_text:
            self.license_label.configure(text="")
            return
        text = self._license_text
        if self._collapsed:
            text = text.split(" ")[0] if text else "🔑"
        self.license_label.configure(
            text=text, text_color=self._license_color,
            wraplength=theme.SIDEBAR_WIDTH - 48,
        )

    def set_busy(self, busy: bool) -> None:
        self._busy = busy

    def toggle_collapsed(self) -> None:
        self._collapsed = not self._collapsed
        self._render()
