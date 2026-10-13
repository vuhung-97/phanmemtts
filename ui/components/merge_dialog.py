from __future__ import annotations

import queue
import threading
from tkinter import filedialog

import customtkinter as ctk
import numpy as np

from audio import exporter, mixer
from core.models import MusicMergeConfig, TrackSegment
from ui import theme
from ui.components.segment_timeline import SegmentTimeline

AUDIO_FILTER = [("Audio", "*.mp3;*.wav"), ("MP3", "*.mp3"), ("WAV", "*.wav"),
                ("Tất cả", "*.*")]

_OUT_H = 56
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


class MergeDialog(ctk.CTkToplevel):
    """Popup ghép nhạc — mỗi track có SegmentTimeline kéo thả."""

    def __init__(self, master, export_history: list[str] | None = None,
                 on_merged=None) -> None:
        super().__init__(master)
        self.title("🎵 Ghép nhạc vào file âm thanh")
        # Chiều rộng 100% màn hình, chiều cao tối đa nhưng không vượt màn hình
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{sw}x{min(1010, sh - 50)}+0+0")
        self.minsize(800, 600)
        self.configure(fg_color=theme.DIALOG_BG)
        self.transient(master)
        self.grab_set()

        self._on_merged = on_merged
        self._messages: queue.Queue = queue.Queue()
        self._busy = False

        # Preview player (tua được)
        from audio.player import AudioPlayer
        self._preview_player = AudioPlayer()
        self._preview_active = False
        self._slider_updating = False

        # Các đoạn giọng đọc (nối theo thứ tự)
        self._voice_paths: list[str] = []
        self._voice_durations: list[float] = []

        # intro / bg / outro
        self._intro_path: str | None = None
        self._bg_path: str | None = None
        self._outro_path: str | None = None
        self._intro_dur: float = 0.0
        self._bg_dur: float = 0.0
        self._outro_dur: float = 0.0

        self._build_ui(export_history or [])
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", lambda _: self._on_close())
        self.after(80, self._poll_messages)

    # ── UI ──

    def _build_ui(self, export_history: list[str]) -> None:
        self.grid_columnconfigure(0, weight=1)
        row = 0

        # ── File gốc (nhiều đoạn nối tiếp) ──
        self._section("File gốc — bấm ＋ để ghép thêm đoạn (.mp3 / .wav)", row)
        row += 1

        self._voice_list = ctk.CTkFrame(self, fg_color="transparent")
        self._voice_list.grid(row=row, column=0, padx=20, pady=(2, 2),
                              sticky="ew")
        self._voice_list.grid_columnconfigure(1, weight=1)
        row += 1

        voice_btn_row = ctk.CTkFrame(self, fg_color="transparent")
        voice_btn_row.grid(row=row, column=0, padx=20, pady=(2, 4), sticky="ew")
        row += 1
        self._voice_btn_row = voice_btn_row

        # History Quick-pick: chọn nhanh file đã xuất gần đây
        if export_history:
            hist_row = ctk.CTkFrame(self, fg_color="transparent")
            hist_row.grid(row=row, column=0, padx=20, pady=(0, 4), sticky="ew")
            hist_row.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(hist_row, text="Gần đây:",
                         text_color=theme.TEXT_DIM,
                         font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1)).grid(
                row=0, column=0, padx=(0, 6))
            self.voice_combo = ctk.CTkComboBox(
                hist_row, state="readonly", values=export_history,
                command=self._on_history_pick, height=30,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE),
                dropdown_font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            )
            self.voice_combo.set(export_history[0])
            self.voice_combo.grid(row=0, column=1, sticky="ew")
            row += 1

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
        xf_row = ctk.CTkFrame(self, fg_color="transparent")
        xf_row.grid(row=row, column=0, padx=20, pady=(2, 8), sticky="w")

        self.crossfade_entry = ctk.CTkEntry(
            xf_row, width=80, height=32,
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
            self, highlightthickness=0, bg=theme.SURFACE, height=_OUT_H,
        )
        self._out_canvas.grid(row=row, column=0, padx=20, pady=(2, 4),
                              sticky="ew")
        self._out_canvas.bind("<Configure>", lambda _: self._update_output_timeline())
        row += 1

        self._out_ruler = ctk.CTkLabel(
            self, text="", text_color=theme.TEXT_DIM,
            font=(theme.FONT_FAMILY, 9),
        )
        self._out_ruler.grid(row=row, column=0, padx=20, sticky="w")
        row += 1

        # ── Buttons (căn giữa, không kéo 100% cho gọn) ──
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=row, column=0, padx=20, pady=(8, 4), sticky="ew")
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
            fg_color=theme.SUCCESS, hover_color="#3d9a6c", corner_radius=8,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
            command=self._start_merge,
        )
        self.merge_btn.grid(row=0, column=2, padx=(6, 0), sticky="")
        row += 1

        # ── Thanh tua khi nghe thử ──
        seek_row = ctk.CTkFrame(self, fg_color=theme.SURFACE, corner_radius=8)
        seek_row.grid(row=row, column=0, padx=20, pady=(4, 4), sticky="ew")
        seek_row.grid_columnconfigure(1, weight=1)

        self._prev_cur = ctk.CTkLabel(seek_row, text="00:00", width=50,
                                      text_color=theme.TEXT,
                                      font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"))
        self._prev_cur.grid(row=0, column=0, padx=(10, 4), pady=8, sticky="w")

        self._seek_slider = ctk.CTkSlider(
            seek_row, from_=0.0, to=1.0, state="disabled",
            progress_color=theme.ACCENT, button_color=theme.ACCENT,
            command=self._on_seek_slider,
        )
        self._seek_slider.set(0.0)
        self._seek_slider.grid(row=0, column=1, padx=4, pady=8, sticky="ew")

        self._prev_total = ctk.CTkLabel(seek_row, text="00:00", width=50,
                                        text_color=theme.TEXT_DIM,
                                        font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"))
        self._prev_total.grid(row=0, column=2, padx=(4, 4), pady=8, sticky="e")

        self._stop_preview_btn = ctk.CTkButton(
            seek_row, text="⏹", width=36, height=28, state="disabled",
            fg_color="transparent", border_width=1, border_color=theme.ERROR,
            text_color=theme.ERROR, hover_color=theme.SURFACE, corner_radius=6,
            command=self._stop_preview,
        )
        self._stop_preview_btn.grid(row=0, column=3, padx=(0, 10), pady=8)
        row += 1

        # ── Status ──
        self.status_label = ctk.CTkLabel(
            self, text="", text_color=theme.TEXT_DIM, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            wraplength=self.winfo_screenwidth() - 80,
        )
        self.status_label.grid(row=100, column=0, padx=20, pady=(8, 16),
                               sticky="sew")
        self.grid_rowconfigure(100, weight=1)

    def _section(self, text: str, row: int) -> None:
        ctk.CTkLabel(
            self, text=text, text_color=theme.TEXT_DIM, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
        ).grid(row=row, column=0, padx=20, pady=(8, 0), sticky="w")

    def _track_row(self, key: str, title: str, row: int,
                   default_vol: int) -> ctk.CTkLabel:
        self._section(title, row)

        body = ctk.CTkFrame(self, fg_color=theme.SURFACE, corner_radius=8)
        body.grid(row=row + 1, column=0, padx=20, pady=(2, 4), sticky="ew")
        body.grid_columnconfigure(0, weight=1)

        # Top: path + buttons
        top = ctk.CTkFrame(body, fg_color="transparent")
        top.grid(row=0, column=0, padx=10, pady=(8, 2), sticky="ew")
        top.grid_columnconfigure(0, weight=1)

        path_label = ctk.CTkLabel(
            top, text="Chưa chọn", text_color=theme.TEXT_DIM, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
        )
        path_label.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        ctk.CTkButton(
            top, text="📁", width=36, height=28,
            fg_color="transparent", border_width=1, border_color=theme.ACCENT,
            text_color=theme.ACCENT, hover_color=theme.SURFACE, corner_radius=6,
            command=lambda k=key: self._browse_track(k),
        ).grid(row=0, column=1, padx=(0, 4))

        ctk.CTkButton(
            top, text="✕", width=28, height=28,
            fg_color="transparent", border_width=1, border_color=theme.ERROR,
            text_color=theme.ERROR, hover_color=theme.SURFACE, corner_radius=6,
            command=lambda k=key, lbl=path_label: self._clear_track(k, lbl),
        ).grid(row=0, column=2)

        # SegmentTimeline
        timeline = SegmentTimeline(body, on_change=lambda s, e, k=key:
                                   self._on_segment_change(k))
        timeline.grid(row=1, column=0, padx=10, pady=(2, 2), sticky="ew")

        # Volume + duration
        vol_row = ctk.CTkFrame(body, fg_color="transparent")
        vol_row.grid(row=2, column=0, padx=10, pady=(2, 8), sticky="ew")
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
        }
        if key == "intro":
            self._intro_refs = refs
        elif key == "bg":
            self._bg_refs = refs
        else:
            self._outro_refs = refs

        return path_label

    # ── Segment change callback ──

    def _on_segment_change(self, key: str) -> None:
        refs = getattr(self, f"_{key}_refs")
        start, end = refs["timeline"].get_range()
        refs["dur"].configure(text=f"Đoạn: {end - start:.1f}s")
        self._update_output_timeline()

    # ── Chọn file ──

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
                ).grid(row=i, column=0, padx=(4, 0), pady=2, sticky="w")

                ctk.CTkLabel(
                    self._voice_list, text=path, anchor="w",
                    text_color=theme.TEXT,
                    font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
                ).grid(row=i, column=1, padx=6, pady=2, sticky="ew")

                ctk.CTkButton(
                    self._voice_list, text="✕", width=28, height=26,
                    fg_color="transparent", border_width=1,
                    border_color=theme.ERROR, text_color=theme.ERROR,
                    hover_color=theme.SURFACE, corner_radius=6,
                    command=lambda idx=i: self._remove_voice(idx),
                ).grid(row=i, column=2, padx=(0, 4), pady=2)

        # Nút thêm / chọn file
        for w in self._voice_btn_row.winfo_children():
            w.destroy()
        if not self._voice_paths:
            ctk.CTkButton(
                self._voice_btn_row, text="📁  Chọn file gốc", width=200,
                height=32, fg_color="transparent", border_width=1,
                border_color=theme.ACCENT, text_color=theme.ACCENT,
                hover_color=theme.SURFACE, corner_radius=8,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
                command=lambda: self._add_voice(),
            ).grid(row=0, column=0, sticky="w")
        else:
            ctk.CTkButton(
                self._voice_btn_row, text="＋  Thêm đoạn", width=160,
                height=32, fg_color="transparent", border_width=1,
                border_color=theme.ACCENT, text_color=theme.ACCENT,
                hover_color=theme.SURFACE, corner_radius=8,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
                command=lambda: self._add_voice(),
            ).grid(row=0, column=0, sticky="w")

            ctk.CTkLabel(
                self._voice_btn_row,
                text=f"{len(self._voice_paths)} đoạn sẽ được nối theo thứ tự",
                text_color=theme.TEXT_DIM,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1),
            ).grid(row=0, column=1, padx=(10, 0), sticky="w")

    def _add_voice(self, path: str | None = None) -> None:
        if path is None:
            path = filedialog.askopenfilename(
                title="Chọn file âm thanh (nối vào đoạn gốc)",
                filetypes=AUDIO_FILTER)
        if not path:
            return
        self._voice_paths.append(path)
        self._render_voice_list()
        self._update_output_timeline()
        threading.Thread(target=self._load_voice_durs_worker,
                         args=(list(self._voice_paths),), daemon=True).start()

    def _remove_voice(self, index: int) -> None:
        if not 0 <= index < len(self._voice_paths):
            return
        del self._voice_paths[index]
        if index < len(self._voice_durations):
            del self._voice_durations[index]
        self._render_voice_list()
        self._update_output_timeline()

    def _on_history_pick(self, value: str) -> None:
        if value and value != "(chưa có file)":
            self._add_voice(value)

    def _load_voice_durs_worker(self, paths: list[str]) -> None:
        try:
            import soundfile as sf
            durs = [sf.info(p).duration for p in paths]
            self._messages.put(("voice_durs", list(paths), durs))
        except Exception as exc:
            self._messages.put(("error", str(exc)))

    def _browse_track(self, key: str) -> None:
        path = filedialog.askopenfilename(
            title=f"Chọn nhạc: {key}", filetypes=AUDIO_FILTER)
        if not path:
            return
        refs = getattr(self, f"_{key}_refs")
        refs["path_label"].configure(text=path, text_color=theme.TEXT)
        setattr(self, f"_{key}_path", path)
        threading.Thread(target=self._load_peaks_worker,
                         args=(path, key), daemon=True).start()

    def _load_peaks_worker(self, path: str, key: str) -> None:
        try:
            peaks, duration = mixer.get_peaks(path, num_bars=150)
            self._messages.put(("peaks", key, peaks, duration))
        except Exception as exc:
            self._messages.put(("error", str(exc)))

    def _clear_track(self, key: str, path_label) -> None:
        setattr(self, f"_{key}_path", None)
        setattr(self, f"_{key}_dur", 0.0)
        path_label.configure(text="Chưa chọn", text_color=theme.TEXT_DIM)
        refs = getattr(self, f"_{key}_refs")
        refs["timeline"].clear()
        refs["dur"].configure(text="Đoạn: —")
        self._update_output_timeline()

    # ── Config ──

    def _get_crossfade(self) -> float:
        try:
            v = float(self.crossfade_entry.get().strip() or "0")
        except ValueError:
            v = 0.5
        return max(0.0, min(v, 10.0))

    def _make_segment(self, key: str) -> TrackSegment | None:
        path = getattr(self, f"_{key}_path")
        if not path:
            return None
        refs = getattr(self, f"_{key}_refs")
        start, end = refs["timeline"].get_range()
        return TrackSegment(path=path, start_sec=start, end_sec=end)

    def _build_config(self) -> MusicMergeConfig | None:
        if not self._voice_paths:
            self._set_status("Chưa chọn file gốc.", theme.ERROR)
            return None
        return MusicMergeConfig(
            voice_paths=list(self._voice_paths),
            intro=self._make_segment("intro"),
            bg=self._make_segment("bg"),
            outro=self._make_segment("outro"),
            intro_volume=self._intro_refs["slider"].get() / 100.0,
            bg_volume=self._bg_refs["slider"].get() / 100.0,
            outro_volume=self._outro_refs["slider"].get() / 100.0,
            crossfade_sec=self._get_crossfade(),
        )

    # ── Output timeline ──

    def _update_output_timeline(self) -> None:
        c = self._out_canvas
        c.delete("all")
        W = c.winfo_width()
        H = c.winfo_height()
        if W <= 1:
            return

        c.create_rectangle(0, 0, W, H, fill=theme.SURFACE, outline="")

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
                          fill=theme.TEXT_DIM,
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
            segments_info = (name, x, x + bw)
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

    # ── Preview (nghe thử + tua) ──

    def _preview(self) -> None:
        if self._busy:
            return
        config = self._build_config()
        if config is None:
            return
        self._set_busy(True)
        self._set_status("Đang trộn để nghe thử...", theme.TEXT_DIM)
        threading.Thread(target=self._preview_worker, args=(config,),
                         daemon=True).start()

    def _preview_worker(self, config) -> None:
        try:
            waveform, sr = mixer.merge(config)
            self._messages.put(("preview_ready", waveform, sr))
        except Exception as exc:
            self._messages.put(("error", str(exc)))

    def _start_preview_playback(self, waveform, sr: int) -> None:
        self._set_busy(False)
        self._preview_player.stop()
        self._preview_player.load(waveform, sr, has_more=False)
        self._preview_player.play()
        duration = len(waveform) / sr if sr > 0 else 0.0
        self._slider_updating = True
        try:
            self._seek_slider.configure(to=max(duration, 0.001), state="normal")
            self._seek_slider.set(0.0)
        finally:
            self._slider_updating = False
        self._prev_cur.configure(text="00:00")
        self._prev_total.configure(text=_fmt_clock(duration))
        self._stop_preview_btn.configure(state="normal")
        self._preview_active = True
        self._set_status("Đang phát nghe thử — kéo thanh để tua.",
                         theme.SUCCESS)

    def _on_seek_slider(self, value: float) -> None:
        if self._slider_updating or not self._preview_active:
            return
        self._preview_player.seek(float(value))
        self._prev_cur.configure(text=_fmt_clock(float(value)))

    def _stop_preview(self) -> None:
        self._preview_player.stop()
        self._preview_active = False
        self._slider_updating = True
        try:
            self._seek_slider.set(0.0)
            self._seek_slider.configure(state="disabled")
        finally:
            self._slider_updating = False
        self._prev_cur.configure(text="00:00")
        self._stop_preview_btn.configure(state="disabled")
        self._set_status("Đã dừng nghe thử.", theme.TEXT_DIM)

    def _update_preview_tick(self) -> None:
        if not self._preview_active:
            return
        ended = self._preview_player.update()
        if self._preview_player.is_playing or self._preview_player.is_buffering:
            pos = self._preview_player.get_position()
            self._slider_updating = True
            try:
                self._seek_slider.set(pos)
            finally:
                self._slider_updating = False
            self._prev_cur.configure(text=_fmt_clock(pos))
        if ended:
            self._preview_active = False
            self._slider_updating = True
            try:
                self._seek_slider.set(0.0)
                self._seek_slider.configure(state="disabled")
            finally:
                self._slider_updating = False
            self._prev_cur.configure(text="00:00")
            self._stop_preview_btn.configure(state="disabled")

    # ── Merge & Export ──

    def _start_merge(self) -> None:
        if self._busy:
            return
        config = self._build_config()
        if config is None:
            return
        path = filedialog.asksaveasfilename(
            title="Lưu file đã ghép",
            defaultextension=".mp3",
            filetypes=[("MP3", "*.mp3"), ("WAV", "*.wav")],
        )
        if not path:
            return
        self._set_busy(True)
        self._set_status("Đang ghép nhạc...", theme.TEXT_DIM)
        threading.Thread(target=self._merge_worker, args=(config, path),
                         daemon=True).start()

    def _merge_worker(self, config, out_path: str) -> None:
        try:
            waveform, sr = mixer.merge(config)
            out = exporter.export(waveform, sr, out_path)
            self._messages.put(("merged", str(out)))
        except Exception as exc:
            self._messages.put(("error", str(exc)))

    # ── Helpers ──

    def _set_status(self, msg: str, color: str = theme.TEXT_DIM) -> None:
        self.status_label.configure(text=msg, text_color=color)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        state = "disabled" if busy else "normal"
        self.preview_btn.configure(state=state)
        self.merge_btn.configure(state=state)

    def _poll_messages(self) -> None:
        try:
            while True:
                msg = self._messages.get_nowait()
                kind = msg[0]
                if kind == "peaks":
                    _, key, peaks, duration = msg
                    refs = getattr(self, f"_{key}_refs")
                    refs["timeline"].set_audio(peaks, duration)
                    setattr(self, f"_{key}_dur", duration)
                    s, e = refs["timeline"].get_range()
                    refs["dur"].configure(text=f"Đoạn: {e - s:.1f}s")
                    self._update_output_timeline()
                elif kind == "voice_durs":
                    _, paths, durs = msg
                    if paths == self._voice_paths:
                        self._voice_durations = durs
                        self._update_output_timeline()
                elif kind == "preview_ready":
                    _, waveform, sr = msg
                    self._start_preview_playback(waveform, sr)
                elif kind == "status":
                    _, text, color = msg
                    self._set_status(text, color)
                elif kind == "merged":
                    _, path = msg
                    self._set_busy(False)
                    self._set_status(f"✓ Đã ghép thành công → {path}",
                                     theme.SUCCESS)
                    if self._on_merged:
                        self._on_merged(path)
                elif kind == "error":
                    _, text = msg
                    self._set_busy(False)
                    self._set_status(f"Lỗi: {text}", theme.ERROR)
                elif kind == "done":
                    self._set_busy(False)
        except queue.Empty:
            pass
        self._update_preview_tick()
        self.after(80, self._poll_messages)

    def _on_close(self) -> None:
        try:
            self._preview_player.quit()
        except Exception:
            pass
        self.destroy()
