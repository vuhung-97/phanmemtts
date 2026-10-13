from __future__ import annotations

import queue
import threading
from tkinter import filedialog

import customtkinter as ctk
import numpy as np

from audio import exporter, mixer
from core.models import MusicMergeConfig
from ui import theme

AUDIO_FILTER = [("Audio", "*.mp3;*.wav"), ("MP3", "*.mp3"), ("WAV", "*.wav"),
                ("Tất cả", "*.*")]
CROSSFADE_OPTIONS = ["0.0s", "0.3s", "0.5s", "1.0s"]


class MergeDialog(ctk.CTkToplevel):
    """Popup ghép nhạc vào file âm thanh."""

    def __init__(self, master, export_history: list[str] | None = None,
                 on_merged=None) -> None:
        super().__init__(master)
        self.title("🎵 Ghép nhạc vào file âm thanh")
        self.geometry("560x680")
        self.minsize(480, 560)
        self.configure(fg_color=theme.DIALOG_BG)
        self.transient(master)
        self.grab_set()

        self._on_merged = on_merged
        self._messages: queue.Queue = queue.Queue()
        self._busy = False

        self._voice_path: str | None = None
        self._intro_path: str | None = None
        self._bg_path: str | None = None
        self._outro_path: str | None = None

        self._build_ui(export_history or [])
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", lambda _: self._on_close())
        self.after(80, self._poll_messages)

    # ── UI ──

    def _build_ui(self, export_history: list[str]) -> None:
        self.grid_columnconfigure(0, weight=1)
        row = 0

        # ── File gốc ──
        self._section("File gốc (.mp3 / .wav)", row)
        row += 1

        voice_row = ctk.CTkFrame(self, fg_color="transparent")
        voice_row.grid(row=row, column=0, padx=20, pady=(2, 4), sticky="ew")
        voice_row.grid_columnconfigure(0, weight=1)

        values = export_history if export_history else ["(chưa có file)"]
        self.voice_combo = ctk.CTkComboBox(
            voice_row, state="readonly", values=values,
            command=self._on_voice_combo, height=32,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            dropdown_font=(theme.FONT_FAMILY, theme.FONT_SIZE),
        )
        self.voice_combo.set(values[0])
        self.voice_combo.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        ctk.CTkButton(
            voice_row, text="📁", width=40, height=32,
            fg_color=theme.SURFACE, border_width=1, border_color=theme.ACCENT,
            text_color=theme.ACCENT, hover_color=theme.SURFACE, corner_radius=6,
            command=self._browse_voice,
        ).grid(row=0, column=1)

        self.voice_label = ctk.CTkLabel(
            self, text="Chưa chọn file", text_color=theme.TEXT_DIM, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1), wraplength=520,
        )
        self.voice_label.grid(row=row + 1, column=0, padx=20, sticky="w")
        row += 2

        # ── Intro ──
        self._intro_label = self._track_row("Nhạc mở đầu (intro)", row,
                                            default_vol=70)
        row += 2

        # ── Background ──
        self._bg_label = self._track_row("Nhạc nền (tự lặp)", row,
                                         default_vol=15)
        row += 2

        # ── Outro ──
        self._outro_label = self._track_row("Nhạc kết thúc (outro)", row,
                                            default_vol=70)
        row += 2

        # ── Crossfade ──
        self._section("Chuyển đoạn (crossfade)", row)
        row += 1
        self.crossfade_combo = ctk.CTkComboBox(
            self, state="readonly", values=CROSSFADE_OPTIONS,
            width=120, height=32, command=lambda _: None,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            dropdown_font=(theme.FONT_FAMILY, theme.FONT_SIZE),
        )
        self.crossfade_combo.set("0.5s")
        self.crossfade_combo.grid(row=row, column=0, padx=20, pady=(2, 8),
                                  sticky="w")
        row += 1

        # ── Buttons ──
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=row, column=0, padx=20, pady=(4, 4), sticky="ew")
        btn_row.grid_columnconfigure((0, 1), weight=1)

        self.preview_btn = ctk.CTkButton(
            btn_row, text="▶  Nghe thử", height=36,
            fg_color="transparent", border_width=1, border_color=theme.ACCENT,
            text_color=theme.ACCENT, hover_color=theme.SURFACE, corner_radius=8,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
            command=self._preview,
        )
        self.preview_btn.grid(row=0, column=0, padx=(0, 4), sticky="ew")

        self.merge_btn = ctk.CTkButton(
            btn_row, text="💾  Ghép & Xuất file", height=36,
            fg_color=theme.SUCCESS, hover_color="#3d9a6c", corner_radius=8,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
            command=self._start_merge,
        )
        self.merge_btn.grid(row=0, column=1, padx=(4, 0), sticky="ew")
        row += 1

        # ── Status ──
        self.status_label = ctk.CTkLabel(
            self, text="", text_color=theme.TEXT_DIM, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE), wraplength=520,
        )
        self.status_label.grid(row=100, column=0, padx=20, pady=(8, 16),
                               sticky="sew")
        self.grid_rowconfigure(100, weight=1)

    def _section(self, text: str, row: int) -> None:
        ctk.CTkLabel(
            self, text=text, text_color=theme.TEXT_DIM, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE, "bold"),
        ).grid(row=row, column=0, padx=20, pady=(8, 0), sticky="w")

    def _track_row(self, title: str, row: int, default_vol: int) -> ctk.CTkLabel:
        self._section(title, row)

        body = ctk.CTkFrame(self, fg_color=theme.SURFACE, corner_radius=8)
        body.grid(row=row + 1, column=0, padx=20, pady=(2, 4), sticky="ew")
        body.grid_columnconfigure(0, weight=1)

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
            command=lambda: self._browse_track(title),
        ).grid(row=0, column=1, padx=(0, 4))

        ctk.CTkButton(
            top, text="✕", width=28, height=28,
            fg_color="transparent", border_width=1, border_color=theme.ERROR,
            text_color=theme.ERROR, hover_color=theme.SURFACE, corner_radius=6,
            command=lambda: self._clear_track(title),
        ).grid(row=0, column=2)

        vol_row = ctk.CTkFrame(body, fg_color="transparent")
        vol_row.grid(row=1, column=0, padx=10, pady=(2, 8), sticky="ew")
        vol_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(vol_row, text="Volume:", text_color=theme.TEXT_DIM,
                     font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1)).grid(
            row=0, column=0, sticky="w")

        slider = ctk.CTkSlider(
            vol_row, from_=0, to=100, number_of_steps=20, width=180,
        )
        slider.set(default_vol)
        slider.grid(row=0, column=1, padx=(4, 6))

        pct_label = ctk.CTkLabel(vol_row, text=f"{default_vol}%",
                                 text_color=theme.TEXT, width=40,
                                 font=(theme.FONT_FAMILY, theme.FONT_SIZE - 1))
        pct_label.grid(row=0, column=2)

        slider.configure(command=lambda v, lbl=pct_label: lbl.configure(
            text=f"{int(float(v))}%"))

        # Lưu tham chiếu
        title_key = title.lower()
        if "intro" in title_key or "mở đầu" in title_key:
            self._intro_slider, self._intro_pct = slider, pct_label
        elif "nền" in title_key or "background" in title_key:
            self._bg_slider, self._bg_pct = slider, pct_label
        else:
            self._outro_slider, self._outro_pct = slider, pct_label

        return path_label

    # ── Chọn file ──

    def _on_voice_combo(self, value: str) -> None:
        if value and value != "(chưa có file)":
            self._voice_path = value
            self.voice_label.configure(text=value, text_color=theme.TEXT)

    def _browse_voice(self) -> None:
        path = filedialog.askopenfilename(title="Chọn file gốc",
                                          filetypes=AUDIO_FILTER)
        if path:
            self._voice_path = path
            self.voice_label.configure(text=path, text_color=theme.TEXT)
            self.voice_combo.set(path.split("/")[-1].split("\\")[-1])

    def _browse_track(self, title: str) -> None:
        path = filedialog.askopenfilename(title=f"Chọn nhạc: {title}",
                                          filetypes=AUDIO_FILTER)
        if not path:
            return
        name = title.lower()
        if "mở đầu" in name or "intro" in name:
            self._intro_path = path
            self._intro_label.configure(text=path, text_color=theme.TEXT)
        elif "nền" in name or "background" in name:
            self._bg_path = path
            self._bg_label.configure(text=path, text_color=theme.TEXT)
        else:
            self._outro_path = path
            self._outro_label.configure(text=path, text_color=theme.TEXT)

    def _clear_track(self, title: str) -> None:
        name = title.lower()
        if "mở đầu" in name or "intro" in name:
            self._intro_path = None
            self._intro_label.configure(text="Chưa chọn", text_color=theme.TEXT_DIM)
        elif "nền" in name or "background" in name:
            self._bg_path = None
            self._bg_label.configure(text="Chưa chọn", text_color=theme.TEXT_DIM)
        else:
            self._outro_path = None
            self._outro_label.configure(text="Chưa chọn", text_color=theme.TEXT_DIM)

    # ── Config ──

    def _build_config(self) -> MusicMergeConfig | None:
        if not self._voice_path:
            self._set_status("Chưa chọn file gốc.", theme.ERROR)
            return None
        return MusicMergeConfig(
            voice_path=self._voice_path,
            intro_path=self._intro_path,
            bg_path=self._bg_path,
            outro_path=self._outro_path,
            intro_volume=self._intro_slider.get() / 100.0,
            bg_volume=self._bg_slider.get() / 100.0,
            outro_volume=self._outro_slider.get() / 100.0,
            crossfade_sec=float(self.crossfade_combo.get().replace("s", "")),
        )

    # ── Preview ──

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
            import sounddevice as sd

            waveform, sr = mixer.merge(config)
            sd.stop()
            sd.play(waveform, sr)
            self._messages.put(("status", "Đang phát nghe thử...", theme.SUCCESS))
        except Exception as exc:
            self._messages.put(("error", str(exc)))
        finally:
            self._messages.put(("done",))

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
                if kind == "status":
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
        self.after(80, self._poll_messages)

    def _on_close(self) -> None:
        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass
        self.destroy()
