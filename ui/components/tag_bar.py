"""Thanh chèn nhanh thẻ điều khiển ngay trên khung soạn thảo.

- 3 thẻ cảm xúc: model VieNeu tự đọc thành tiếng cười / thở dài / hắng giọng.
- Thẻ nghỉ: app chèn khoảng lặng đúng số giây (core/tags.py).
"""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from core.tags import format_pause
from ui import theme

_PAUSE_CHOICES: tuple[tuple[str, float], ...] = (
    ("1s", 1.0),
    ("2s", 2.0),
    ("3s", 3.0),
    ("5s", 5.0),
)


class TagBar(ctk.CTkFrame):
    """Hàng nút chèn nhanh: [cười] [thở dài] [hắng giọng] + [nghỉ Ns].

    Bên phải có thêm 2 công cụ soạn thảo: ``📖 Từ điển`` và ``🧹 Làm sạch``.
    """

    def __init__(self, master, on_insert: Callable[[str], None],
                 on_dictionary: Callable[[], None] | None = None,
                 on_clean: Callable[[], None] | None = None) -> None:
        super().__init__(master, fg_color="transparent")
        self._on_insert = on_insert

        ctk.CTkLabel(
            self, text="Chèn nhanh:", text_color=theme.TEXT_DIM,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
        ).pack(side="left", padx=(2, 6))

        for tag in ("[cười]", "[thở dài]", "[hắng giọng]"):
            ctk.CTkButton(
                self, text=tag, height=28, width=0,
                fg_color="transparent", border_width=1, border_color=theme.ACCENT,
                text_color=theme.ACCENT, hover_color=theme.HOVER_BG,
                corner_radius=6,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
                command=lambda t=tag: self._on_insert(t),
            ).pack(side="left", padx=(0, 6))

        ctk.CTkLabel(
            self, text="│", text_color=theme.SIDEBAR_DIVIDER,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
        ).pack(side="left", padx=(2, 6))

        self.pause_btn = ctk.CTkButton(
            self, text="⏸  Nghỉ", height=28, width=0,
            fg_color="transparent", border_width=1, border_color=theme.SUCCESS,
            text_color=theme.SUCCESS_HOVER, hover_color=theme.HOVER_BG,
            corner_radius=6,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            command=self._insert_pause,
        )
        self.pause_btn.pack(side="left", padx=(0, 6))

        self.pause_menu = ctk.CTkOptionMenu(
            self, values=[label for label, _ in _PAUSE_CHOICES], width=68, height=28,
            fg_color=theme.INPUT_BG, button_color=theme.SURFACE,
            button_hover_color=theme.HOVER_BG, text_color=theme.TEXT,
            dropdown_fg_color=theme.SURFACE, dropdown_text_color=theme.TEXT,
            dropdown_hover_color=theme.HOVER_BG, corner_radius=6,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
        )
        self.pause_menu.set("2s")
        self.pause_menu.pack(side="left", padx=(0, 10))

        # ── Công cụ soạn thảo (bên phải, không đẩy các nút thẻ sang trái) ──
        self.clean_btn = None
        if on_clean is not None:
            self.clean_btn = ctk.CTkButton(
                self, text="🧹 Làm sạch", height=28, width=0,
                fg_color="transparent", border_width=1,
                border_color=theme.SIDEBAR_DIVIDER, text_color=theme.TEXT,
                hover_color=theme.HOVER_BG, corner_radius=6,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
                command=on_clean,
            )
            self.clean_btn.pack(side="right", padx=(6, 2))

        self.dict_btn = None
        if on_dictionary is not None:
            self.dict_btn = ctk.CTkButton(
                self, text="📖 Từ điển", height=28, width=0,
                fg_color="transparent", border_width=1,
                border_color=theme.ACCENT, text_color=theme.ACCENT,
                hover_color=theme.HOVER_BG, corner_radius=6,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
                command=on_dictionary,
            )
            self.dict_btn.pack(side="right", padx=(6, 2))

        self._hint_label = ctk.CTkLabel(
            self, text=self.DEFAULT_HINT,
            text_color=theme.TEXT_DIM, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
        )
        self._hint_label.pack(side="left", fill="x", expand=True)

    #: Gợi ý mặc định khi văn bản không có thẻ lạ.
    DEFAULT_HINT = "Thẻ đặt trong câu; thẻ nghỉ chèn khoảng lặng đúng số giây."

    def set_hint(self, text: str | None = None, error: bool = False) -> None:
        """Đổi dòng gợi ý (dùng để cảnh báo thẻ chưa hỗ trợ)."""
        self._hint_label.configure(
            text=text or self.DEFAULT_HINT,
            text_color=theme.ERROR if error else theme.TEXT_DIM,
        )

    def selected_pause_sec(self) -> float:
        label = self.pause_menu.get()
        for name, sec in _PAUSE_CHOICES:
            if name == label:
                return sec
        return 2.0

    def _insert_pause(self) -> None:
        self._on_insert(format_pause(self.selected_pause_sec()))
