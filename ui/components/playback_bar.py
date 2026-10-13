from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from ui import theme


def format_time(seconds: float) -> str:
    seconds = max(int(seconds), 0)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


class PlaybackBar(ctk.CTkFrame):
    """Thanh seekbar, đồng hồ thời gian và các nút điều khiển phát."""

    def __init__(
        self,
        master,
        on_toggle: Callable[[], None],
        on_seek: Callable[[float], None],
        on_prev_sentence: Callable[[], None],
        on_next_sentence: Callable[[], None],
    ) -> None:
        super().__init__(master, fg_color=theme.SURFACE, corner_radius=10,
                         border_width=1, border_color=theme.SIDEBAR_DIVIDER)
        self._on_toggle = on_toggle
        self._on_seek = on_seek
        self._on_prev = on_prev_sentence
        self._on_next = on_next_sentence
        self._duration = 0.0
        self._updating_slider = False

        self.grid_columnconfigure(1, weight=1)

        self.time_label = ctk.CTkLabel(
            self, text="00:00", width=55,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"), text_color=theme.TEXT,
        )
        self.time_label.grid(row=0, column=0, padx=(12, 6), pady=(10, 2), sticky="w")

        self.slider = ctk.CTkSlider(
            self, from_=0.0, to=1.0, command=self._slider_moved,
            progress_color=theme.ACCENT, button_color=theme.ACCENT,
        )
        self.slider.set(0.0)
        self.slider.grid(row=0, column=1, padx=6, pady=(10, 2), sticky="ew")

        self.total_label = ctk.CTkLabel(
            self, text="00:00", width=55,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"), text_color=theme.TEXT_DIM,
        )
        self.total_label.grid(row=0, column=2, padx=(6, 12), pady=(10, 2), sticky="e")

        btn_kw = dict(
            width=86, height=32, fg_color=theme.SURFACE, border_width=1,
            border_color=theme.SIDEBAR_DIVIDER, text_color=theme.TEXT,
            hover_color=theme.HOVER_BG,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
        )
        self.prev_btn = ctk.CTkButton(self, text="⏮ Câu trước", command=self._on_prev, **btn_kw)
        self.rew_btn = ctk.CTkButton(self, text="⏪ -5s", command=lambda: self._skip(-5), **btn_kw)
        self.toggle_btn = ctk.CTkButton(
            self, text="▶ Phát", width=120, height=32, fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER, command=self._on_toggle,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
        )
        self.fwd_btn = ctk.CTkButton(self, text="⏩ +5s", command=lambda: self._skip(5), **btn_kw)
        self.next_btn = ctk.CTkButton(self, text="⏭ Câu sau", command=self._on_next, **btn_kw)

        self.prev_btn.grid(row=1, column=0, padx=(12, 3), pady=(2, 10), sticky="e")
        self.rew_btn.grid(row=1, column=1, padx=3, pady=(2, 10), sticky="w")
        self.toggle_btn.grid(row=1, column=1, padx=3, pady=(2, 10))
        self.fwd_btn.grid(row=1, column=1, padx=3, pady=(2, 10), sticky="e")
        self.next_btn.grid(row=1, column=2, padx=(3, 12), pady=(2, 10), sticky="w")

    def _skip(self, delta: float) -> None:
        current = self.slider.get()
        self._on_seek(max(current + delta, 0.0))

    def _slider_moved(self, value: float) -> None:
        if not self._updating_slider:
            self.time_label.configure(text=format_time(value))
            self._on_seek(float(value))

    def set_duration(self, duration: float) -> None:
        self._duration = duration
        self.slider.configure(to=max(duration, 0.001))
        self.total_label.configure(text=format_time(duration))

    def set_position(self, seconds: float) -> None:
        self._updating_slider = True
        try:
            self.slider.set(min(seconds, self._duration))
            self.time_label.configure(text=format_time(seconds))
        finally:
            self._updating_slider = False

    def set_playing(self, playing: bool) -> None:
        self.toggle_btn.configure(text="⏸ Tạm dừng" if playing else "▶ Phát")
