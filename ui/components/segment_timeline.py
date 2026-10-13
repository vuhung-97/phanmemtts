from __future__ import annotations

from typing import Callable

import numpy as np
import customtkinter as ctk

from ui import theme

_HEIGHT = 44
_HANDLE_PX = 10          # bán kính nhận diện handle
_MIN_SEGMENT_SEC = 0.5   # đoạn ngắn nhất


def _fmt(sec: float) -> str:
    sec = max(0.0, sec)
    m = int(sec // 60)
    s = sec - m * 60
    if m > 0:
        return f"{m}:{s:04.1f}"
    return f"{s:.1f}s"


class SegmentTimeline(ctk.CTkFrame):
    """Waveform mini với 2 handle kéo thả để chọn đoạn start/end."""

    def __init__(self, master,
                 on_change: Callable[[float, float], None] | None = None) -> None:
        super().__init__(master, fg_color=theme.TIMELINE_BG, corner_radius=6,
                         height=_HEIGHT + 8)
        self.grid_propagate(False)
        self._on_change = on_change

        self._peaks: np.ndarray | None = None
        self._duration: float = 0.0
        self._start: float = 0.0
        self._end: float = 0.0
        self._dragging: str | None = None   # "start" | "end" | "move"
        self._drag_offset: float = 0.0

        self._canvas = ctk.CTkCanvas(
            self, highlightthickness=0, bg=theme.TIMELINE_BG, height=_HEIGHT,
        )
        self._canvas.grid(row=0, column=0, sticky="nsew", padx=2, pady=(2, 0))
        self.grid_columnconfigure(0, weight=1)

        self._canvas.bind("<Configure>", lambda _: self._redraw())
        self._canvas.bind("<ButtonPress-1>", self._on_press)
        self._canvas.bind("<B1-Motion>", self._on_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_release)
        self._canvas.bind("<Motion>", self._on_motion)

    # ── Public API ──

    def set_audio(self, peaks: np.ndarray, duration: float) -> None:
        """Nạp peaks (0..1) + duration → set full range."""
        self._peaks = np.asarray(peaks, dtype=np.float32)
        self._duration = max(float(duration), 0.01)
        self._start = 0.0
        self._end = self._duration
        self._redraw()
        self._notify()

    def get_range(self) -> tuple[float, float]:
        return self._start, self._end

    def set_range(self, start: float, end: float) -> None:
        self._start = max(0.0, min(start, self._duration))
        self._end = max(self._start + _MIN_SEGMENT_SEC, min(end, self._duration))
        self._end = min(self._end, self._duration)
        self._redraw()

    def clear(self) -> None:
        self._peaks = None
        self._duration = 0.0
        self._start = 0.0
        self._end = 0.0
        self._canvas.delete("all")

    # ── Coordinate helpers ──

    def _x_to_sec(self, x: float) -> float:
        W = self._canvas.winfo_width()
        if W <= 0:
            return 0.0
        return (x / W) * self._duration

    def _sec_to_x(self, sec: float) -> float:
        if self._duration <= 0:
            return 0.0
        return (sec / self._duration) * self._canvas.winfo_width()

    # ── Mouse ──

    def _on_press(self, event) -> None:
        if self._peaks is None or self._duration <= 0:
            return
        x = event.x
        start_x = self._sec_to_x(self._start)
        end_x = self._sec_to_x(self._end)

        if abs(x - start_x) <= _HANDLE_PX:
            self._dragging = "start"
        elif abs(x - end_x) <= _HANDLE_PX:
            self._dragging = "end"
        elif start_x < x < end_x:
            self._dragging = "move"
            self._drag_offset = self._x_to_sec(x) - self._start
        else:
            # Snap nearest handle rồi drag
            if abs(x - start_x) < abs(x - end_x):
                self._dragging = "start"
                self._start = self._x_to_sec(x)
            else:
                self._dragging = "end"
                self._end = self._x_to_sec(x)
            self._clamp()
            self._redraw()
            self._notify()

    def _on_drag(self, event) -> None:
        if self._dragging is None or self._duration <= 0:
            return
        x = event.x
        sec = self._x_to_sec(x)

        if self._dragging == "start":
            self._start = max(0.0, min(sec, self._end - _MIN_SEGMENT_SEC))
        elif self._dragging == "end":
            self._end = min(self._duration, max(sec, self._start + _MIN_SEGMENT_SEC))
        elif self._dragging == "move":
            seg_len = self._end - self._start
            new_start = sec - self._drag_offset
            new_start = max(0.0, min(new_start, self._duration - seg_len))
            self._start = new_start
            self._end = new_start + seg_len

        self._redraw()
        self._notify()

    def _on_release(self, _event) -> None:
        self._dragging = None

    def _on_motion(self, event) -> None:
        if self._peaks is None or self._duration <= 0:
            return
        x = event.x
        start_x = self._sec_to_x(self._start)
        end_x = self._sec_to_x(self._end)
        if abs(x - start_x) <= _HANDLE_PX or abs(x - end_x) <= _HANDLE_PX:
            self._canvas.configure(cursor="sb_h_double_arrow")
        elif start_x < x < end_x:
            self._canvas.configure(cursor="fleur")
        else:
            self._canvas.configure(cursor="")

    def _clamp(self) -> None:
        self._start = max(0.0, min(self._start, self._duration))
        self._end = max(self._start + _MIN_SEGMENT_SEC, min(self._end, self._duration))

    def _notify(self) -> None:
        if self._on_change:
            self._on_change(self._start, self._end)

    # ── Render ──

    def _redraw(self) -> None:
        c = self._canvas
        c.delete("all")
        W = c.winfo_width()
        H = c.winfo_height()
        if W <= 1:
            return

        # Background
        c.create_rectangle(0, 0, W, H, fill=theme.TIMELINE_BG, outline="")

        if self._peaks is None or len(self._peaks) == 0 or self._duration <= 0:
            c.create_text(W // 2, H // 2, text="Chọn file nhạc...",
                          fill=theme.TIMELINE_TEXT,
                          font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1))
            return

        start_x = self._sec_to_x(self._start)
        end_x = self._sec_to_x(self._end)
        mid_y = H / 2

        # Waveform bars
        n = len(self._peaks)
        bar_w = max(1, W / n)
        for i, peak in enumerate(self._peaks):
            x = i * W / n
            h = max(1, peak * (H - 16))
            in_sel = start_x <= x + bar_w / 2 <= end_x
            color = theme.TIMELINE_TEXT if in_sel else theme.WAVE_DIM
            c.create_rectangle(x, mid_y - h / 2, x + bar_w, mid_y + h / 2,
                               fill=color, outline="")

        # Dim overlay ngoài vùng chọn
        if start_x > 0:
            c.create_rectangle(0, 0, start_x, H, fill=theme.BG,
                               stipple="gray50", outline="")
        if end_x < W:
            c.create_rectangle(end_x, 0, W, H, fill=theme.BG,
                               stipple="gray50", outline="")

        # Handles
        self._draw_handle(c, start_x, H, is_start=True)
        self._draw_handle(c, end_x, H, is_start=False)

        # Time labels
        c.create_text(start_x, H - 2, text=_fmt(self._start),
                      fill=theme.TEXT, anchor="n",
                      font=(theme.FONT_FAMILY, 9, "bold"))
        c.create_text(end_x, H - 2, text=_fmt(self._end),
                      fill=theme.TEXT, anchor="n",
                      font=(theme.FONT_FAMILY, 9, "bold"))

    def _draw_handle(self, c, x: float, H: int, is_start: bool) -> None:
        # Vertical line
        c.create_line(x, 0, x, H, fill=theme.TIMELINE_HANDLE, width=2)
        # Triangle
        if is_start:
            c.create_polygon(x, 0, x + 8, 4, x, 8, fill=theme.TIMELINE_HANDLE,
                             outline="")
        else:
            c.create_polygon(x, 0, x - 8, 4, x, 8, fill=theme.TIMELINE_HANDLE,
                             outline="")
