from __future__ import annotations

import queue
import threading
from tkinter import filedialog

import customtkinter as ctk

from audio import exporter, mixer
from audio.buffer import GrowableBuffer
from audio.player import AudioPlayer
from core.licensing import guard
from core.models import MusicMergeConfig, TrackSegment
from ui import theme
from ui.components.merge_widgets import (AUDIO_FILTER, MergeWidgetsMixin,
                                         _fmt_clock)
from ui.shell.page import Page
from ui.ui_kit import Button


class MergePage(MergeWidgetsMixin, Page):
    """Trang Ghép nhạc: intro / nền / outro + crossfade, preview dùng player chung."""

    _TRACK_LABELS = {"intro": "intro", "bg": "nhạc nền", "outro": "outro"}

    def __init__(self, master, ctx, **kwargs) -> None:
        super().__init__(master, ctx, page_id="merge", title="Ghép nhạc",
                         subtitle="Intro / nhạc nền / outro · crossfade", **kwargs)

        self._messages: queue.Queue = queue.Queue()
        self._busy = False
        self._active = False

        # Preview dùng AudioPlayer riêng; điều khiển qua PlayerBar chung
        self._preview_player = AudioPlayer()
        self._preview_active = False

        self._voice_paths: list[str] = []
        self._voice_durations: list[float] = []
        self._intro_path: str | None = None
        self._bg_path: str | None = None
        self._outro_path: str | None = None
        self._intro_dur = 0.0
        self._bg_dur = 0.0
        self._outro_dur = 0.0

        self.pick_btn = Button(self.header.actions, text="📁  Chọn file gốc",
                               variant="secondary",
                               command=lambda: self._add_voice())
        self.pick_btn.pack(side="left", padx=(0, theme.SPACE_SM))
        self.preview_btn = Button(self.header.actions, text="▶  Nghe thử",
                                  variant="secondary", command=self._preview)
        self.preview_btn.pack(side="left", padx=(0, theme.SPACE_SM))
        self.merge_btn = Button(self.header.actions, text="💾  Ghép & Xuất",
                                variant="primary", command=self._start_merge)
        self.merge_btn.pack(side="left")

        self._build_ui(self.body, list(getattr(ctx, "_export_history", []) or []))

    # ── vòng đời ──

    def on_show(self) -> None:
        self._active = True
        self._bind_player()
        self.after(80, self._poll_messages)
        self.after(40, self._tick)

    def on_hide(self) -> None:
        self._active = False
        self._stop_preview()
        self._restore_player()

    def _bind_player(self) -> None:
        bar = self.ctx.shell.player_bar
        bar.set_handlers(
            toggle=self._toggle_preview,
            seek=self._seek_preview,
            prev=lambda: self._seek_relative(-5),
            next=lambda: self._seek_relative(5),
            speed=lambda _v: self._set_status(
                "Ghép nhạc không dùng tốc độ.", theme.TEXT_DIM),
        )
        bar.set_speed_enabled(False)

    def _restore_player(self) -> None:
        bar = self.ctx.shell.player_bar
        bar.set_handlers(
            toggle=self.ctx._toggle_play,
            seek=self.ctx._seek,
            prev=self.ctx._prev_sentence,
            next=self.ctx._next_sentence,
            speed=self.ctx._on_speed_change,
        )
        bar.set_speed_enabled(True)

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        state = "disabled" if busy else "normal"
        self.preview_btn.configure(state=state)
        self.merge_btn.configure(state=state)

    # ── preview ──

    def _toggle_preview(self) -> None:
        if not self._preview_active:
            self._set_status("Bấm “Nghe thử” để tạo bản nghe thử trước.",
                             theme.TEXT_DIM)
            return
        self._preview_player.toggle()
        self.ctx.shell.player_bar.set_playing(
            self._preview_player.is_playing)

    def _seek_preview(self, seconds: float) -> None:
        if not self._preview_active:
            return
        self._preview_player.seek(float(seconds))
        self.ctx.shell.player_bar.set_position(
            self._preview_player.get_position())

    def _seek_relative(self, delta: float) -> None:
        if not self._preview_active:
            return
        pos = max(0.0, self._preview_player.get_position() + delta)
        self._seek_preview(pos)

    def _tick(self) -> None:
        if not self._active:
            return
        if self._preview_active:
            ended = self._preview_player.update()
            bar = self.ctx.shell.player_bar
            if self._preview_player.is_playing or self._preview_player.is_buffering:
                bar.set_position(self._preview_player.get_position())
                bar.set_playing(self._preview_player.is_playing)
            if ended:
                self._preview_active = False
                bar.set_playing(False)
                bar.set_position(0.0)
        self.after(40, self._tick)

    def _start_preview_playback(self, waveform, sr: int,
                                label: str | None = None) -> None:
        self.set_busy(False)
        self._preview_player.stop()
        self._preview_player.load(waveform, sr, has_more=False)
        self._preview_player.play()

        source = GrowableBuffer()
        source.append(waveform)
        bar = self.ctx.shell.player_bar
        bar.set_source(source, sr)
        bar.set_duration(len(waveform) / sr if sr > 0 else 0.0)
        bar.set_position(0.0)
        bar.set_playing(True)
        self._preview_active = True
        if label:
            self._set_status(f"▶ Đang nghe thử {label} — tua trên thanh dưới.",
                             theme.SUCCESS)
        else:
            self._set_status("Đang phát nghe thử — tua trên thanh dưới.",
                             theme.SUCCESS)

    def _stop_preview(self) -> None:
        try:
            self._preview_player.stop()
        except Exception:
            pass
        self._preview_active = False
        if hasattr(self.ctx, "shell"):
            self.ctx.shell.player_bar.set_playing(False)
            self.ctx.shell.player_bar.set_position(0.0)

    # ── chọn file ──

    def _add_voice(self, path: str | None = None) -> None:
        if path is None:
            path = filedialog.askopenfilename(
                title="Chọn file âm thanh (nối vào đoạn gốc)",
                filetypes=AUDIO_FILTER, parent=self)
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

    # ── track nhạc ──

    def _on_segment_change(self, key: str) -> None:
        refs = getattr(self, f"_{key}_refs")
        start, end = refs["timeline"].get_range()
        refs["dur"].configure(text=f"Đoạn: {end - start:.1f}s")
        self._update_output_timeline()

    def _browse_track(self, key: str) -> None:
        path = filedialog.askopenfilename(
            title=f"Chọn nhạc: {key}", filetypes=AUDIO_FILTER, parent=self)
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

    # ── config / merge ──

    def _get_crossfade(self) -> float:
        try:
            value = float(self.crossfade_entry.get().strip() or "0")
        except ValueError:
            value = 0.5
        return max(0.0, min(value, 10.0))

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

    def _preview(self) -> None:
        if self._busy:
            return
        config = self._build_config()
        if config is None:
            return
        self.set_busy(True)
        self._set_status("Đang trộn để nghe thử...", theme.TEXT_DIM)
        threading.Thread(target=self._preview_worker, args=(config,),
                         daemon=True).start()

    def _preview_worker(self, config) -> None:
        try:
            waveform, sr = mixer.merge(config)
            self._messages.put(("preview_ready", waveform, sr))
        except Exception as exc:
            self._messages.put(("error", str(exc)))

    def _start_merge(self) -> None:
        if self._busy:
            return
        if not self.ctx._ensure_license("ghép nhạc"):
            return
        config = self._build_config()
        if config is None:
            return
        path = filedialog.asksaveasfilename(
            title="Lưu file đã ghép", defaultextension=".mp3",
            filetypes=[("MP3", "*.mp3"), ("WAV", "*.wav")], parent=self)
        if not path:
            return
        self.set_busy(True)
        self._set_status("Đang ghép nhạc...", theme.TEXT_DIM)
        threading.Thread(target=self._merge_worker, args=(config, path),
                         daemon=True).start()

    def _merge_worker(self, config, out_path: str) -> None:
        try:
            if not guard.check_startup().active:
                self._messages.put(("error", "Thiết bị chưa kích hoạt — "
                                            "không thể xuất file."))
                return
            waveform, sr = mixer.merge(config)
            out = exporter.export(waveform, sr, out_path)
            duration = len(waveform) / sr if sr else 0.0
            self._messages.put(("merged", str(out), duration,
                                len(config.voice_paths)))
        except Exception as exc:
            self._messages.put(("error", str(exc)))

    # ── message loop ──

    def _set_status(self, msg: str, color: str = theme.TEXT_DIM) -> None:
        self.status_label.configure(text=msg, text_color=color)

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
                    _, path, duration, parts = msg
                    self.set_busy(False)
                    try:
                        self.ctx._history.add(
                            path, voice="Ghép nhạc", speed=1.0,
                            duration=duration, chars=0,
                            preview=f"Ghép nhạc: {parts} đoạn")
                        history = self.ctx._export_history
                        history.append(path)
                        del history[:-10]
                    except Exception:
                        pass
                    self._set_status(f"✓ Đã ghép thành công → {path}",
                                     theme.SUCCESS)
                    self.ctx.shell.status(f"Đã ghép: {path}", theme.SUCCESS)
                elif kind == "error":
                    _, text = msg
                    self.set_busy(False)
                    self._set_status(f"Lỗi: {text}", theme.ERROR)
                elif kind == "done":
                    self.set_busy(False)
        except queue.Empty:
            pass
        if self._active:
            self.after(80, self._poll_messages)
