from __future__ import annotations

import queue
import threading
from tkinter import filedialog

import customtkinter as ctk

from audio import exporter, mixer
from core.models import MusicMergeConfig, TrackSegment
from ui import theme
from ui.components.merge_widgets import (AUDIO_FILTER, MergeWidgetsMixin,
                                         _fmt_clock)


class MergeDialog(MergeWidgetsMixin, ctk.CTkToplevel):
    """Popup ghép nhạc — mỗi track có SegmentTimeline kéo thả."""

    def __init__(self, master, export_history: list[str] | None = None,
                 on_merged=None) -> None:
        super().__init__(master)
        self.title("🎵 Ghép nhạc vào file âm thanh")
        # Kích thước 900 x 700 (vừa màn 768px), nội dung cuộn trong CTkScrollableFrame
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w, h = 900, min(700, sh - 60)
        x = max((sw - w) // 2, 0)
        y = max((sh - h) // 2, 0)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(900, 500)
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

    # ── Segment change callback ──

    def _on_segment_change(self, key: str) -> None:
        refs = getattr(self, f"_{key}_refs")
        start, end = refs["timeline"].get_range()
        refs["dur"].configure(text=f"Đoạn: {end - start:.1f}s")
        self._update_output_timeline()

    # ── Chọn file ──

    # ── Các đoạn giọng đọc (nối tiếp) ──

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
            self._history_sel = value
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
        refs["play_btn"].configure(state="normal")
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
        refs["play_btn"].configure(state="disabled")
        self._update_output_timeline()

    # ── Nghe thử từng track ──

    _TRACK_LABELS = {"intro": "intro", "bg": "nhạc nền", "outro": "outro"}

    def _preview_track(self, key: str) -> None:
        if self._busy:
            return
        path = getattr(self, f"_{key}_path")
        refs = getattr(self, f"_{key}_refs")
        if not path:
            self._set_status("Chưa chọn file cho đoạn này.", theme.ERROR)
            return
        start, end = refs["timeline"].get_range()
        if end - start < 0.05:
            self._set_status("Vùng chọn quá ngắn — hãy chọn lại đoạn.",
                             theme.ERROR)
            return
        if self._preview_active:
            self._stop_preview()
        volume = refs["slider"].get() / 100.0
        label = self._TRACK_LABELS.get(key, key)
        self._set_status(f"Đang nạp {label}...", theme.TEXT_DIM)
        threading.Thread(target=self._preview_track_worker,
                         args=(path, start, end, volume, label),
                         daemon=True).start()

    def _preview_track_worker(self, path: str, start: float, end: float,
                              volume: float, label: str) -> None:
        try:
            audio, sr = mixer.load_audio(path)
            seg = mixer.extract_segment(audio, sr, start, end)
            seg = mixer.apply_volume(seg, volume)
            if len(seg) == 0:
                raise ValueError("Đoạn rỗng — kiểm tra lại vùng chọn.")
            self._messages.put(("preview_ready", seg, sr, label))
        except Exception as exc:
            self._messages.put(("error", str(exc)))

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

    def _start_preview_playback(self, waveform, sr: int,
                                label: str | None = None) -> None:
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
        if label:
            self._set_status(f"▶ Đang nghe thử {label} — kéo thanh để tua.",
                             theme.SUCCESS)
        else:
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
                    if len(msg) == 4:
                        _, waveform, sr, label = msg
                        self._start_preview_playback(waveform, sr, label)
                    else:
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
