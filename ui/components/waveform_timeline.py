from __future__ import annotations

import numpy as np
import customtkinter as ctk

from ui import theme

_NUM_BARS = 300
_HEIGHT = 88
_WAVEFORM_AREA = 44   # px trên cho waveform
_RULER_AREA = 32      # px dưới cho time ruler


def _format_time(seconds: float) -> str:
    seconds = max(int(seconds), 0)
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"


class WaveformTimeline(ctk.CTkFrame):
    """Waveform hiển thị — chỉ xem, không kéo thả. Seek qua PlaybackBar."""

    def __init__(self, master) -> None:
        super().__init__(master, fg_color=theme.TIMELINE_BG, corner_radius=8,
                         height=_HEIGHT)
        self.grid_propagate(False)

        self._peaks: np.ndarray | None = None
        self._duration: float = 0.0
        self._sentence_bounds: list[tuple[float, float]] = []
        self._position: float = 0.0

        # Canvas full-bleed -> tự vẽ nền + viền + góc bo (frame bị canvas che)
        self._canvas = ctk.CTkCanvas(
            self, highlightthickness=0, bg=theme.BG, height=_HEIGHT,
        )
        self._canvas.grid(row=0, column=0, sticky="nsew")
        self.grid_columnconfigure(0, weight=1)

        self._canvas.bind("<Configure>", lambda _: self._redraw())

    # ── Vẽ nền bo góc + viền (arc chuẩn, 4 góc đối xứng cùng bán kính) ──

    _R = 8   # bằng corner_radius của frame/card khác trong app

    # (ô vuông góc, hộp đường tròn, start, extent) cho 4 góc
    def _corner_specs(self, W: int, H: int):
        r = self._R
        return [
            ((0, 0, r, r), (0, 0, 2 * r, 2 * r), 90, 90),                 # trái-trên
            ((W - r, 0, W, r), (W - 2 * r, 0, W, 2 * r), 0, 90),          # phải-trên
            ((W - r, H - r, W, H), (W - 2 * r, H - 2 * r, W, H), 270, 90),  # phải-dưới
            ((0, H - r, r, H), (0, H - 2 * r, 2 * r, H), 180, 90),        # trái-dưới
        ]

    def _paint_background(self, c, W: int, H: int) -> None:
        c.create_rectangle(0, 0, W, H, fill=theme.BG, outline="")
        c.create_rectangle(0, 0, W, H, fill=theme.TIMELINE_BG, outline="")

    def _clip_corners(self, c, W: int, H: int) -> None:
        """Đục 4 góc về màu nền ngoài, vẽ lại 1/4 tròn -> bo góc thật."""
        for (sx1, sy1, sx2, sy2), (bx1, by1, bx2, by2), start, extent in \
                self._corner_specs(W, H):
            c.create_rectangle(sx1, sy1, sx2, sy2, fill=theme.BG, outline="")
            c.create_arc(bx1, by1, bx2, by2, start=start, extent=extent,
                         style="pieslice", fill=theme.TIMELINE_BG, outline="")

    # ── Public API ──

    def set_audio(self, waveform: np.ndarray, sample_rate: int,
                  sentences: list | None = None) -> None:
        """Nạp waveform → tính peaks + duration → vẽ."""
        if waveform is None or len(waveform) == 0 or sample_rate <= 0:
            self.clear()
            return
        mono = np.asarray(waveform, dtype=np.float32)
        self._duration = len(mono) / sample_rate

        bucket = max(1, len(mono) // _NUM_BARS)
        peaks = np.array([
            np.max(np.abs(mono[i:i + bucket]))
            for i in range(0, len(mono), bucket)
        ])[:_NUM_BARS]
        if peaks.max() > 0:
            peaks = peaks / peaks.max()
        self._peaks = peaks.astype(np.float32)

        self._sentence_bounds = []
        if sentences:
            for s in sentences:
                self._sentence_bounds.append((s.start_sec, s.end_sec))

        self._redraw()

    def append_chunk(self, waveform: np.ndarray, sample_rate: int,
                     sentences: list | None = None) -> None:
        """Streaming: nạp lại toàn bộ waveform + sentence (gọi từ stream_chunk)."""
        self.set_audio(waveform, sample_rate, sentences)

    def update_position(self, seconds: float) -> None:
        """Di chuyển playhead (gọi từ tick mỗi ~40ms)."""
        self._position = max(0.0, seconds)
        self._redraw()

    def clear(self) -> None:
        self._peaks = None
        self._duration = 0.0
        self._sentence_bounds = []
        self._position = 0.0
        self._canvas.delete("all")

    # ── Render ──

    def _redraw(self) -> None:
        c = self._canvas
        c.delete("all")
        W = c.winfo_width()
        H = c.winfo_height()
        if W <= 1:
            return

        wave_h = _WAVEFORM_AREA

        # Nền vuông -> nội dung -> đục 4 góc bo -> viền
        self._paint_background(c, W, H)

        if self._peaks is None or len(self._peaks) == 0:
            c.create_text(W // 2, H // 2, text="Chưa có âm thanh",
                          fill=theme.TIMELINE_TEXT,
                          font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1))
            self._clip_corners(c, W, H)
            return

        # Waveform bars
        n = len(self._peaks)
        bar_w = max(1, W / n)
        mid_y = wave_h / 2 + 4
        playhead_px = (self._position / self._duration * W) if self._duration > 0 else 0

        for i, peak in enumerate(self._peaks):
            x = i * W / n
            h = max(1, peak * (wave_h - 8))
            color = theme.TIMELINE_TEXT if x <= playhead_px else "#e6eefb"
            c.create_rectangle(x, mid_y - h / 2, x + bar_w, mid_y + h / 2,
                               fill=color, outline="")

        # Sentence markers
        for start_sec, end_sec in self._sentence_bounds:
            sx = start_sec / self._duration * W if self._duration > 0 else 0
            if 0 < sx < W:
                c.create_line(sx, 0, sx, wave_h + 4, fill=theme.TIMELINE_DIM,
                              width=1)

        # Playhead
        if playhead_px > 0:
            c.create_line(playhead_px, 0, playhead_px, wave_h + 6,
                          fill="#0d1728", width=2)
            # Triangle nhỏ trên đầu
            c.create_polygon(playhead_px - 4, 0, playhead_px + 4, 0,
                             playhead_px, 7, fill="#0d1728", outline="")

        # Time ruler
        self._draw_ruler(c, W, H)

        # Đục góc bo + viền sau cùng để cắt content tràn ra ngoài
        self._clip_corners(c, W, H)

    def _draw_ruler(self, c, W: int, H: int) -> None:
        if self._duration <= 0:
            return
        # Chọn step sao cho nhãn cách nhau tối thiểu ~60px
        for step in (5, 10, 15, 30, 60, 120, 300, 600):
            if step / self._duration * W >= 60:
                break
        else:
            step = 600

        tick_y = H - 20
        text_y = H - 16   # anchor="n": text chiếm [H-16, H-1] — không bao giờ cắt đáy

        t = 0.0
        while t <= self._duration + 0.01:
            x = t / self._duration * W
            if 0 <= x <= W:
                c.create_line(x, tick_y - 5, x, tick_y,
                              fill=theme.TIMELINE_TEXT, width=1)
                if x < 30:
                    # tránh nhãn chạm góc bo tròn bottom-left/right
                    anchor, x_draw = "w", max(x, 10)
                elif x > W - 30:
                    anchor, x_draw = "e", min(x, W - 10)
                else:
                    anchor, x_draw = "center", x
                c.create_text(x_draw, text_y, text=_format_time(t),
                              fill=theme.TIMELINE_TEXT, anchor=anchor,
                              font=(theme.FONT_FAMILY, 9, "bold"))
            t += step
