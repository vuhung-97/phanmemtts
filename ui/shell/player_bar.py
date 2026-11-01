from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from ui import theme
from ui.components.waveform_timeline import WaveformTimeline
from ui.ui_kit import Button


def _format_time(seconds: float) -> str:
    seconds = max(int(seconds), 0)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


class PlayerBar(ctk.CTkFrame):
    """Thanh phát dùng chung: waveform + seek + transport + tốc độ."""

    def __init__(
        self,
        master,
        on_toggle: Callable[[], None],
        on_seek: Callable[[float], None],
        on_prev_sentence: Callable[[], None],
        on_next_sentence: Callable[[], None],
        on_speed_change: Callable[[float], None],
        **kwargs,
    ) -> None:
        kwargs.setdefault("fg_color", theme.SURFACE)
        kwargs.setdefault("corner_radius", 0)
        kwargs.setdefault("height", theme.PLAYER_HEIGHT)
        super().__init__(master, **kwargs)
        self.grid_propagate(False)
        self.grid_columnconfigure(1, weight=1)

        self._on_toggle = on_toggle
        self._on_seek = on_seek
        self._on_prev = on_prev_sentence
        self._on_next = on_next_sentence
        self._on_speed_change = on_speed_change
        self._duration = 0.0
        self._position = 0.0

        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.grid(row=0, column=0, padx=(theme.SPACE_LG, theme.SPACE_SM),
                      pady=theme.SPACE_MD, sticky="w")

        self.prev_btn = Button(controls, text="⏮", variant="ghost", size="sm",
                               width=34, command=self._on_prev)
        self.prev_btn.pack(side="left", padx=1)
        self.rew_btn = Button(controls, text="−5s", variant="ghost", size="sm",
                              width=38, command=lambda: self._skip(-5))
        self.rew_btn.pack(side="left", padx=1)
        self.toggle_btn = Button(controls, text="▶", variant="primary", size="md",
                                 width=44, command=self._on_toggle)
        self.toggle_btn.pack(side="left", padx=theme.SPACE_XS)
        self.fwd_btn = Button(controls, text="+5s", variant="ghost", size="sm",
                              width=38, command=lambda: self._skip(5))
        self.fwd_btn.pack(side="left", padx=1)
        self.next_btn = Button(controls, text="⏭", variant="ghost", size="sm",
                               width=34, command=self._on_next)
        self.next_btn.pack(side="left", padx=1)

        self.waveform = WaveformTimeline(self)
        self.waveform.grid(row=0, column=1, padx=theme.SPACE_SM,
                           pady=(theme.SPACE_MD, theme.SPACE_XS), sticky="nsew")
        self.waveform.bind_seek(self._seek_from_waveform)

        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=0, column=2, padx=(theme.SPACE_SM, theme.SPACE_LG),
                   pady=theme.SPACE_MD, sticky="e")

        self.time_label = ctk.CTkLabel(
            right, text="00:00 / 00:00", width=104, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1, "bold"),
            text_color=theme.TEXT,
        )
        self.time_label.pack(side="top", anchor="w")

        speed_row = ctk.CTkFrame(right, fg_color="transparent")
        speed_row.pack(side="top", anchor="w", pady=(2, 0))
        ctk.CTkLabel(
            speed_row, text="Tốc độ",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 2),
            text_color=theme.TEXT_DIM,
        ).pack(side="left", padx=(0, theme.SPACE_XS))
        self.speed_combo = ctk.CTkComboBox(
            speed_row, width=74, height=28, state="readonly",
            values=["0.5x", "0.75x", "1.0x", "1.25x", "1.5x", "1.75x", "2.0x"],
            command=self._speed_changed, corner_radius=theme.RADIUS_SM,
            fg_color=theme.INPUT_BG, text_color=theme.INPUT_TEXT,
            border_color=theme.BORDER, border_width=1,
            button_color=theme.SURFACE_2, button_hover_color=theme.HOVER_BG,
            dropdown_fg_color=theme.SURFACE, dropdown_text_color=theme.TEXT,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            dropdown_font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
        )
        self.speed_combo.set("1.0x")
        self.speed_combo.pack(side="left")

    # ── transport ──

    def _skip(self, delta: float) -> None:
        self._on_seek(max(self._position + delta, 0.0))

    def _seek_from_waveform(self, seconds: float) -> None:
        self._on_seek(seconds)

    def _speed_changed(self, value: str) -> None:
        self._on_speed_change(float(value.replace("x", "")))

    # ── API (tương thích PlaybackBar cũ) ──

    def set_duration(self, duration: float) -> None:
        self._duration = max(0.0, float(duration))
        self._refresh_time()

    def set_position(self, seconds: float) -> None:
        self._position = max(0.0, float(seconds))
        self._refresh_time()

    def get_position(self) -> float:
        return self._position

    def set_playing(self, playing: bool) -> None:
        self.toggle_btn.configure(text="⏸" if playing else "▶")

    def set_source(self, source, sample_rate: int, sentences=None) -> None:
        self.waveform.set_source(source, sample_rate, sentences)

    def update_position(self, seconds: float) -> None:
        self._position = max(0.0, float(seconds))
        self.waveform.update_position(seconds)
        self._refresh_time()

    def clear(self) -> None:
        self._duration = 0.0
        self._position = 0.0
        self.waveform.clear()
        self._refresh_time()

    def get_speed(self) -> float:
        return float(self.speed_combo.get().replace("x", ""))

    def set_speed(self, value: float) -> None:
        self.speed_combo.set(f"{value:g}x")

    def set_visible(self, visible: bool) -> None:
        if visible:
            if not self.winfo_ismapped():
                self.grid()
        else:
            self.grid_remove()

    def _refresh_time(self) -> None:
        self.time_label.configure(
            text=f"{_format_time(self._position)} / {_format_time(self._duration)}")
