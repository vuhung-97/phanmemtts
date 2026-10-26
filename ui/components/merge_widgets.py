from __future__ import annotations

import customtkinter as ctk

from ui import theme
from ui.components.segment_timeline import SegmentTimeline

AUDIO_FILTER = [("Audio", "*.mp3;*.wav"), ("MP3", "*.mp3"), ("WAV", "*.wav"),
                ("Tất cả", "*.*")]

_OUT_H = 48
_INTRO_COLOR = "#3d5a80"
_VOICE_COLOR = "#4caf7d"
_OUTRO_COLOR = "#e8a04a"


def _fmt(sec: float) -> str:
    sec = max(0.0, sec)
    m = int(sec // 60)
    s = sec - m * 60
    return f"{m}:{s:02.0f}" if m > 0 else f"{s:.1f}s"


def _fmt_clock(seconds: float) -> str:
    seconds = max(int(seconds), 0)
    m, s = divmod(seconds, 60)
    return f"{m:02d}:{s:02d}"


class MergeWidgetsMixin:
    """Phần dựng giao diện của MergeDialog (tách để mỗi file < 32 KB)."""

    # ── UI ──

    def _build_ui(self, export_history: list[str]) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Container cuộn toàn bộ dialog (vừa màn 768px, cuộn xuống dùng tiếp)
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=theme.TEXT_DIM,
            scrollbar_button_hover_color=theme.ACCENT,
        )
        self._scroll.grid(row=0, column=0, sticky="nsew")
        self._scroll.grid_columnconfigure(0, weight=1)
        row = 0

        # ── File gốc (nhiều đoạn nối tiếp) ──
        self._section("File gốc — bấm ＋ để ghép thêm đoạn (.mp3 / .wav)", row)
        row += 1

        # Danh sách đoạn gốc — khung cố định ≤100px, nội dung cuộn được
        self._voice_list_box = ctk.CTkFrame(self._scroll, fg_color="transparent",
                                            height=40)
        self._voice_list_box.grid(row=row, column=0, padx=20, pady=(2, 2),
                                  sticky="ew")
        self._voice_list_box.grid_propagate(False)
        self._voice_list_box.grid_rowconfigure(0, weight=1)
        self._voice_list_box.grid_columnconfigure(0, weight=1)

        self._voice_list = ctk.CTkScrollableFrame(
            self._voice_list_box, fg_color="transparent",
            scrollbar_button_color=theme.TEXT_DIM,
            scrollbar_button_hover_color=theme.ACCENT,
        )
        self._voice_list.grid(row=0, column=0, sticky="nsew")
        self._voice_list.grid_columnconfigure(1, weight=1)
        row += 1

        voice_btn_row = ctk.CTkFrame(self._scroll, fg_color="transparent")
        voice_btn_row.grid(row=row, column=0, padx=20, pady=(2, 4), sticky="ew")
        voice_btn_row.grid_columnconfigure(1, weight=1)
        row += 1
        self._voice_btn_row = voice_btn_row
        self._export_history = export_history
        self._history_sel = export_history[0] if export_history else None

        self._render_voice_list()
        row += 1

        # ── Intro ──
        self._intro_label = self._track_row("intro", "Nhạc mở đầu (intro)",
                                            row, default_vol=70)
        row += 2

        # ── Background ──
        self._bg_label = self._track_row("bg", "Nhạc nền (tự lặp)",
                                         row, default_vol=15)
        row += 2

        # ── Outro ──
        self._outro_label = self._track_row("outro", "Nhạc kết thúc (outro)",
                                            row, default_vol=70)
        row += 2

        # ── Crossfade (nhập số tự do, đơn vị giây) ──
        self._section("Chuyển đoạn (crossfade, giây)", row)
        row += 1
        xf_row = ctk.CTkFrame(self._scroll, fg_color="transparent")
        xf_row.grid(row=row, column=0, padx=20, pady=(2, 8), sticky="w")

        self.crossfade_entry = ctk.CTkEntry(
            xf_row, width=80, height=32,
            fg_color=theme.INPUT_BG, text_color=theme.INPUT_TEXT,
            placeholder_text_color=theme.INPUT_PLACEHOLDER,
            border_color=theme.SURFACE,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            placeholder_text="0.5",
        )
        self.crossfade_entry.insert(0, "0.5")
        self.crossfade_entry.grid(row=0, column=0, padx=(0, 6))
        self.crossfade_entry.bind("<KeyRelease>",
                                  lambda _: self._update_output_timeline())
        self.crossfade_entry.bind("<FocusOut>",
                                  lambda _: self._update_output_timeline())

        ctk.CTkLabel(xf_row, text="giây — nhập bất kỳ giá trị nào (vd: 0.8, 2.5)",
                     text_color=theme.TEXT_DIM,
                     font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1)).grid(
            row=0, column=1, sticky="w")
        row += 1

        # ── Output timeline ──
        self._section("Timeline output", row)
        row += 1
        self._out_canvas = ctk.CTkCanvas(
            self._scroll, highlightthickness=0, bg=theme.TIMELINE_BG, height=_OUT_H,
        )
        self._out_canvas.grid(row=row, column=0, padx=20, pady=(2, 4),
                              sticky="ew")
        self._out_canvas.bind("<Configure>", lambda _: self._update_output_timeline())
        row += 1

        self._out_ruler = ctk.CTkLabel(
            self._scroll, text="", text_color=theme.TIMELINE_TEXT,
            font=(theme.FONT_FAMILY, 9, "bold"),
        )
        self._out_ruler.grid(row=row, column=0, padx=20, sticky="w")
        row += 1

        # ── Buttons (căn giữa, không kéo 100% cho gọn) ──
        btn_row = ctk.CTkFrame(self._scroll, fg_color="transparent")
        btn_row.grid(row=row, column=0, padx=20, pady=(6, 4), sticky="ew")
        btn_row.grid_columnconfigure((0, 3), weight=1)
        btn_row.grid_columnconfigure((1, 2), weight=0)

        self.preview_btn = ctk.CTkButton(
            btn_row, text="▶  Nghe thử", width=260, height=36,
            fg_color="transparent", border_width=1, border_color=theme.ACCENT,
            text_color=theme.ACCENT, hover_color=theme.SURFACE, corner_radius=8,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
            command=self._preview,
        )
        self.preview_btn.grid(row=0, column=1, padx=(0, 6), sticky="")

        self.merge_btn = ctk.CTkButton(
            btn_row, text="💾  Ghép & Xuất file", width=300, height=36,
            fg_color=theme.SUCCESS, hover_color=theme.SUCCESS_HOVER, corner_radius=8,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
            command=self._start_merge,
        )
        self.merge_btn.grid(row=0, column=2, padx=(6, 0), sticky="")
        row += 1

        # ── Thanh tua khi nghe thử ──
        seek_row = ctk.CTkFrame(self._scroll, fg_color=theme.SURFACE, corner_radius=8)
        seek_row.grid(row=row, column=0, padx=20, pady=(2, 2), sticky="ew")
        seek_row.grid_columnconfigure(1, weight=1)

        self._prev_cur = ctk.CTkLabel(seek_row, text="00:00", width=50,
                                      text_color=theme.TEXT,
                                      font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"))
        self._prev_cur.grid(row=0, column=0, padx=(10, 4), pady=5, sticky="w")

        self._seek_slider = ctk.CTkSlider(
            seek_row, from_=0.0, to=1.0, state="disabled",
            progress_color=theme.ACCENT, button_color=theme.ACCENT,
            command=self._on_seek_slider,
        )
        self._seek_slider.set(0.0)
        self._seek_slider.grid(row=0, column=1, padx=4, pady=5, sticky="ew")

        self._prev_total = ctk.CTkLabel(seek_row, text="00:00", width=50,
                                        text_color=theme.TEXT_DIM,
                                        font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"))
        self._prev_total.grid(row=0, column=2, padx=(4, 4), pady=5, sticky="e")

        self._stop_preview_btn = ctk.CTkButton(
            seek_row, text="⏹", width=36, height=28, state="disabled",
            fg_color="transparent", border_width=1, border_color=theme.ERROR,
            text_color=theme.ERROR, hover_color=theme.SURFACE, corner_radius=6,
            command=self._stop_preview,
        )
        self._stop_preview_btn.grid(row=0, column=3, padx=(0, 10), pady=5)
        row += 1

        # ── Status ──
        self.status_label = ctk.CTkLabel(
            self._scroll, text="", text_color=theme.TEXT_DIM, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE), wraplength=850,
        )
        self.status_label.grid(row=100, column=0, padx=20, pady=(8, 16),
                               sticky="sew")
        self._scroll.grid_rowconfigure(100, weight=1)

    def _section(self, text: str, row: int) -> None:
        ctk.CTkLabel(
            self._scroll, text=text, text_color=theme.TEXT_DIM, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
        ).grid(row=row, column=0, padx=20, pady=(3, 0), sticky="w")

    def _track_row(self, key: str, title: str, row: int,
                   default_vol: int) -> ctk.CTkLabel:
        self._section(title, row)

        body = ctk.CTkFrame(self._scroll, fg_color=theme.SURFACE, corner_radius=8)
        body.grid(row=row + 1, column=0, padx=20, pady=(2, 4), sticky="ew")
        body.grid_columnconfigure(0, weight=1)

        # Top: path + buttons
        top = ctk.CTkFrame(body, fg_color="transparent")
        top.grid(row=0, column=0, padx=10, pady=(4, 2), sticky="ew")
        top.grid_columnconfigure(0, weight=1)

        path_label = ctk.CTkLabel(
            top, text="Chưa chọn", text_color=theme.TEXT_DIM, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
        )
        path_label.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        play_btn = ctk.CTkButton(
            top, text="▶", width=36, height=28, state="disabled",
            fg_color="transparent", border_width=1, border_color=theme.ACCENT,
            text_color=theme.ACCENT, hover_color=theme.SURFACE, corner_radius=6,
            command=lambda k=key: self._preview_track(k),
        )
        play_btn.grid(row=0, column=1, padx=(0, 4))

        ctk.CTkButton(
            top, text="📁", width=36, height=28,
            fg_color="transparent", border_width=1, border_color=theme.ACCENT,
            text_color=theme.ACCENT, hover_color=theme.SURFACE, corner_radius=6,
            command=lambda k=key: self._browse_track(k),
        ).grid(row=0, column=2, padx=(0, 4))

        ctk.CTkButton(
            top, text="✕", width=28, height=28,
            fg_color="transparent", border_width=1, border_color=theme.ERROR,
            text_color=theme.ERROR, hover_color=theme.SURFACE, corner_radius=6,
            command=lambda k=key, lbl=path_label: self._clear_track(k, lbl),
        ).grid(row=0, column=3)

        # SegmentTimeline
        timeline = SegmentTimeline(body, on_change=lambda s, e, k=key:
                                   self._on_segment_change(k))
        timeline.grid(row=1, column=0, padx=10, pady=(2, 2), sticky="ew")

        # Volume + duration
        vol_row = ctk.CTkFrame(body, fg_color="transparent")
        vol_row.grid(row=2, column=0, padx=10, pady=(2, 5), sticky="ew")
        vol_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(vol_row, text="Volume:", text_color=theme.TEXT_DIM,
                     font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1)).grid(
            row=0, column=0, sticky="w")

        slider = ctk.CTkSlider(
            vol_row, from_=0, to=100, number_of_steps=20, width=140,
        )
        slider.set(default_vol)
        slider.grid(row=0, column=1, padx=(4, 6))

        pct_label = ctk.CTkLabel(vol_row, text=f"{default_vol}%",
                                 text_color=theme.TEXT, width=40,
                                 font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1))
        pct_label.grid(row=0, column=2)

        slider.configure(command=lambda v, lbl=pct_label: lbl.configure(
            text=f"{int(float(v))}%"))

        dur_label = ctk.CTkLabel(vol_row, text="Đoạn: —",
                                 text_color=theme.TEXT_DIM, width=80,
                                 font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1))
        dur_label.grid(row=0, column=3, padx=(8, 0))

        # Lưu refs
        refs = {
            "path_label": path_label,
            "timeline": timeline,
            "slider": slider,
            "pct": pct_label,
            "dur": dur_label,
            "play_btn": play_btn,
        }
        if key == "intro":
            self._intro_refs = refs
        elif key == "bg":
            self._bg_refs = refs
        else:
            self._outro_refs = refs

        return path_label

    # ── Các đoạn giọng đọc (nối tiếp) ──

    def _render_voice_list(self) -> None:
        for w in self._voice_list.winfo_children():
            w.destroy()

        if not self._voice_paths:
            ctk.CTkLabel(
                self._voice_list, text="Chưa chọn file gốc",
                text_color=theme.TEXT_DIM, anchor="w",
                font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            ).grid(row=0, column=0, padx=4, pady=4, sticky="w")
        else:
            for i, path in enumerate(self._voice_paths):
                tag = "Gốc" if i == 0 else f"Đoạn {i + 1}"
                ctk.CTkLabel(
                    self._voice_list, text=tag, width=64, anchor="w",
                    text_color=theme.ACCENT,
                    font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1, "bold"),
                ).grid(row=i, column=0, padx=(4, 0), pady=1, sticky="w")

                ctk.CTkLabel(
                    self._voice_list, text=path, anchor="w",
                    text_color=theme.TEXT,
                    font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
                ).grid(row=i, column=1, padx=6, pady=1, sticky="ew")

                ctk.CTkButton(
                    self._voice_list, text="✕", width=28, height=24,
                    fg_color="transparent", border_width=1,
                    border_color=theme.ERROR, text_color=theme.ERROR,
                    hover_color=theme.SURFACE, corner_radius=6,
                    command=lambda idx=i: self._remove_voice(idx),
                ).grid(row=i, column=2, padx=(0, 4), pady=1)

        # Chiều cao khung theo số đoạn — tối đa 100px, vượt thì cuộn
        self._voice_list_box.configure(
            height=100)

        # Nút thêm / chọn file (cùng hàng với quick-pick "Gần đây")
        for w in self._voice_btn_row.winfo_children():
            w.destroy()
        if not self._voice_paths:
            ctk.CTkButton(
                self._voice_btn_row, text="📁  Chọn file gốc", width=180,
                height=30, fg_color="transparent", border_width=1,
                border_color=theme.ACCENT, text_color=theme.ACCENT,
                hover_color=theme.SURFACE, corner_radius=8,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
                command=lambda: self._add_voice(),
            ).grid(row=0, column=0, sticky="w")
        else:
            ctk.CTkButton(
                self._voice_btn_row, text="＋  Thêm đoạn", width=150,
                height=30, fg_color="transparent", border_width=1,
                border_color=theme.ACCENT, text_color=theme.ACCENT,
                hover_color=theme.SURFACE, corner_radius=8,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
                command=lambda: self._add_voice(),
            ).grid(row=0, column=0, sticky="w")

            ctk.CTkLabel(
                self._voice_btn_row,
                text=f"{len(self._voice_paths)} đoạn nối theo thứ tự",
                text_color=theme.TEXT_DIM,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            ).grid(row=0, column=1, padx=(10, 0), sticky="w")

        if self._export_history:
            ctk.CTkLabel(
                self._voice_btn_row, text="Gần đây:",
                text_color=theme.TEXT_DIM,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            ).grid(row=0, column=2, padx=(12, 4), sticky="e")
            combo = ctk.CTkComboBox(
                self._voice_btn_row, state="readonly",
                values=self._export_history,
                command=self._on_history_pick, height=28, width=240,
                fg_color=theme.INPUT_BG, text_color=theme.INPUT_TEXT,
                button_color=theme.SURFACE,
                button_hover_color=theme.ACCENT,
                dropdown_fg_color=theme.INPUT_BG,
                dropdown_text_color=theme.INPUT_TEXT,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
                dropdown_font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            )
            combo.set(self._history_sel or self._export_history[0])
            combo.grid(row=0, column=3, sticky="e")

    # ── Output timeline ──

    def _update_output_timeline(self) -> None:
        c = self._out_canvas
        c.delete("all")
        W = c.winfo_width()
        H = c.winfo_height()
        if W <= 1:
            return

        c.create_rectangle(0, 0, W, H, fill=theme.TIMELINE_BG, outline="")

        fade = self._get_crossfade()
        intro_dur = 0.0
        bg_dur = 0.0
        outro_dur = 0.0

        if self._intro_path:
            s, e = self._intro_refs["timeline"].get_range()
            intro_dur = e - s
        if self._bg_path:
            s, e = self._bg_refs["timeline"].get_range()
            bg_dur = e - s   # hiển thị độ dài đoạn bg (sau loop = voice_dur)
        if self._outro_path:
            s, e = self._outro_refs["timeline"].get_range()
            outro_dur = e - s

        voice_dur = sum(self._voice_durations)

        if intro_dur <= 0 and voice_dur <= 0 and outro_dur <= 0:
            c.create_text(W // 2, H // 2, text="Chọn file để xem timeline",
                          fill=theme.TIMELINE_TEXT,
                          font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1))
            self._out_ruler.configure(text="")
            return

        # Tổng thời lượng output (trừ crossfade theo số điểm nối thực tế)
        joins = (1 if intro_dur > 0 else 0) + (1 if outro_dur > 0 else 0)
        total = max(intro_dur + voice_dur + outro_dur - joins * fade, 0.1)

        # Vẽ blocks
        margin = 4
        inner_w = W - 2 * margin
        x = margin
        segments = []
        if intro_dur > 0:
            segments.append(("intro", intro_dur, _INTRO_COLOR))
        segments.append(("voice", max(voice_dur, 0.5), _VOICE_COLOR))
        if outro_dur > 0:
            segments.append(("outro", outro_dur, _OUTRO_COLOR))

        for name, dur, color in segments:
            bw = dur / total * inner_w
            c.create_rectangle(x, 4, x + bw, H - 4, fill=color, outline="")
            label = name.capitalize() if name != "bg" else "BG"
            if bw > 40:
                c.create_text(x + bw / 2, H / 2, text=label, fill="#fff",
                              font=(theme.FONT_FAMILY, 10, "bold"))
            x += bw

        # Crossfade markers
        x = margin
        for i, (name, dur, color) in enumerate(segments):
            bw = dur / total * inner_w
            if i > 0 and fade > 0:
                # Vùng overlap crossfade
                cx = x
                c.create_rectangle(cx - fade / total * inner_w, 4,
                                   cx + fade / total * inner_w, H - 4,
                                   fill=theme.BG, stipple="gray25", outline="")
            x += bw

        # Ruler
        ruler_parts = []
        if intro_dur > 0:
            ruler_parts.append(f"Intro 0:00→{_fmt(intro_dur)}")
        ruler_parts.append(f"Voice {_fmt(intro_dur)}→{_fmt(intro_dur + voice_dur)}")
        if outro_dur > 0:
            ruler_parts.append(
                f"Outro {_fmt(intro_dur + voice_dur)}→{_fmt(total)}")
        self._out_ruler.configure(text="  |  ".join(ruler_parts))
