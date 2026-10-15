from __future__ import annotations

import queue
import threading
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
import numpy as np

import version
from audio import exporter
from audio.player import AudioPlayer
from audio.speed import apply_speed
from core.models import SentenceItem, TimelineMap
from core.text_processor import build_sentences
from engine.model_manager import ModelManager
from engine.tts_engine import TtsEngine
from ui import theme
from ui.config import load_enabled_voices, save_enabled_voices
from ui.components.topbar import TopBar
from ui.components.playback_bar import PlaybackBar
from ui.components.sync_textbox import SyncTextbox
from ui.components.voice_manager import VoiceManagerDialog
from ui.components.waveform_timeline import WaveformTimeline

TICK_MS = 40
BUFFER_TRIGGER_SENTENCES = 5


class MainWindow(ctk.CTk):
    """Điều phối: TopBar ↔ Textbox ↔ PlaybackBar ↔ TTS Engine."""

    def __init__(self) -> None:
        super().__init__()
        self.title(f"{version.__app_name__} - v{version.__version__}")
        self.geometry("1200x740")
        self.minsize(980, 600)
        ctk.set_appearance_mode("light")
        self.configure(fg_color=theme.BG)

        self._model_manager = ModelManager()
        self._player = AudioPlayer()
        self._messages: queue.Queue = queue.Queue()
        self._worker: threading.Thread | None = None
        self._busy = False
        self._stop_event = threading.Event()

        self._waveform: np.ndarray | None = None
        self._timeline: TimelineMap | None = None
        self._synth_text: str | None = None
        # Bản gốc 1.0x để đổi tốc độ mà không chạy lại model
        self._base_waveform: np.ndarray | None = None
        self._base_timeline: TimelineMap | None = None
        self._applied_speed: float = 1.0     # speed của _waveform hiện tại
        self._speed_dirty: bool = False      # speed đã đổi nhưng chưa áp
        self._speed_applying: bool = False   # guard thread đổi speed
        self._current_sentence = -1
        self._stream_total_sentences = 0
        self._stream_has_started_playing = False

        self._all_models: list = []
        self._export_history: list[str] = []

        self._build_ui()
        self._scan_models()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(TICK_MS, self._tick)

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)

        # ── TopBar (header ngang) ──
        self.topbar = TopBar(
            self,
            on_open_file=self._open_file,
            on_voice_change=self._on_voice_change,
            on_speed_change=self._on_speed_change,
            on_convert=self._start_convert,
            on_stop=self._stop_convert,
            on_export=self._start_export,
            on_manage_voices=self._open_voice_manager,
            on_test_voice=self._test_voice,
        )
        self.topbar.grid(row=0, column=0, sticky="ew")

        # ── Main area (full-width) ──
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 14))
        main.grid_rowconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=0)
        main.grid_rowconfigure(2, weight=0)
        main.grid_columnconfigure(0, weight=1)

        self.textbox = SyncTextbox(main, on_text_changed=self._on_text_changed)
        self.textbox.grid(row=0, column=0, sticky="nsew")

        self.waveform_timeline = WaveformTimeline(main)
        self.waveform_timeline.grid(row=1, column=0, sticky="ew", pady=(6, 0))

        self.playback_bar = PlaybackBar(
            main,
            on_toggle=self._toggle_play,
            on_seek=self._seek,
            on_prev_sentence=self._prev_sentence,
            on_next_sentence=self._next_sentence,
        )
        self.playback_bar.grid(row=2, column=0, sticky="ew", pady=(6, 0))

    # ── Scan & voice management ──

    def _scan_models(self) -> list:
        prev = None
        try:
            prev = self.topbar.get_selected_voice()
        except Exception:
            pass
        self._all_models = self._model_manager.scan()
        if not self._all_models:
            self.topbar.set_status(
                "Không tìm thấy mô hình — chạy download_model.py",
                theme.ERROR,
            )
            return self._all_models

        enabled = load_enabled_voices()
        if enabled is not None:
            visible = [m for m in self._all_models if m.model_id in enabled]
        else:
            visible = self._all_models

        if not visible:
            self.topbar.set_voices([], None)
            self.topbar.set_status(
                "Tất cả giọng đều bị tắt — bấm ＋ Thêm để bật lại.", theme.ERROR)
            return self._all_models

        names = [m.display_name for m in visible]
        selected = prev if prev in names else names[0]
        self.topbar.set_voices(names, selected)
        self.topbar.set_status(
            f"{len(names)}/{len(self._all_models)} giọng sẵn sàng.", theme.TEXT_DIM)
        return self._all_models

    def _selected_model(self):
        name = self.topbar.get_selected_voice()
        for m in self._all_models:
            if m.display_name == name:
                return m
        return None

    def _open_voice_manager(self) -> None:
        enabled = load_enabled_voices()
        if enabled is None:
            enabled = {m.model_id for m in self._all_models}

        def on_save(new_enabled: set[str]) -> None:
            save_enabled_voices(new_enabled)
            self._scan_models()

        def on_voice_changed(name: str) -> None:
            # Ghi đè/xóa giọng đang được nạp -> giải phóng, lần sinh sau tải lại
            self._model_manager.unload_if(f"vieneu:{name}")

        VoiceManagerDialog(
            self, self._all_models, enabled, on_save,
            get_models=self._scan_models,
            on_voice_changed=on_voice_changed,
        )

    # TẠM ẨN chức năng ghép nhạc (không đấu dây từ TopBar).
    # Khôi phục: truyền on_merge=self._open_merge_dialog khi khởi tạo TopBar.
    def _open_merge_dialog(self) -> None:
        from ui.components.merge_dialog import MergeDialog

        MergeDialog(
            self,
            export_history=self._export_history,
            on_merged=lambda path: self.topbar.set_status(
                f"Đã ghép: {path}", theme.SUCCESS),
        )

    # ── Test giọng ──

    def _test_voice(self) -> None:
        model = self._selected_model()
        if model is None:
            self.topbar.set_status("Không có giọng để test.", theme.ERROR)
            return
        test_text = self.topbar.get_test_text()
        speed = self.topbar.get_speed()
        self.topbar.set_status(f"Đang nạp {model.display_name}...", theme.TEXT_DIM)
        threading.Thread(target=self._test_voice_worker,
                         args=(model, test_text, speed), daemon=True).start()

    def _test_voice_worker(self, model, test_text: str, speed: float) -> None:
        try:
            tts = self._model_manager.load_tts(model)
            engine = TtsEngine(tts)
            self._messages.put(("status", "Đang tạo âm thanh test...", theme.TEXT_DIM))
            audio, _ = engine.synthesize(test_text, speed=speed)
            self._messages.put(("status", "Đang phát test...", theme.SUCCESS))
            self._player.load(audio, engine.sample_rate, has_more=False)
            self._player.play()
        except Exception as exc:
            self._messages.put(("error", str(exc)))

    # ── Mở file ──

    def _open_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Chọn file văn bản",
            filetypes=[
                ("Văn bản", "*.docx;*.txt"),
                ("Word Document", "*.docx"),
                ("Text Document", "*.txt"),
                ("Tất cả tập tin", "*.*"),
            ],
        )
        if not path:
            return
        try:
            if path.lower().endswith(".docx"):
                import docx
                doc = docx.Document(path)
                content = "\n".join(p.text for p in doc.paragraphs)
            else:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            self.textbox.set_text(content)
            self.topbar.set_source_name(Path(path).name)
            self.topbar.set_status(f"Đã mở: {path}", theme.SUCCESS)
        except Exception as exc:
            self.topbar.set_status(f"Không mở được file: {exc}", theme.ERROR)

    # ── Callbacks từ topbar ──

    def _on_voice_change(self, _value: str) -> None:
        if self._synth_text is not None:
            self.topbar.set_status(
                "Đã đổi giọng — bấm Chuyển đổi để áp dụng.", theme.TEXT_DIM)

    def _on_speed_change(self, _value: float) -> None:
        if self._busy:
            self._speed_dirty = True
            self.topbar.set_status(
                "Đang chuyển đổi — áp tốc độ này sau khi xong.", theme.TEXT_DIM)
            return
        if self._base_waveform is None or len(self._base_waveform) == 0:
            return
        self._speed_dirty = True
        if self._player.is_playing:
            # Đang phát -> áp ngay, giữ vị trí, phát tiếp không gián đoạn
            self._request_speed_apply(auto_play=False)
        else:
            self.topbar.set_status(
                "Đã đổi tốc độ — bấm Phát để áp dụng.", theme.TEXT_DIM)

    # ── Convert ──

    def _request_speed_apply(self, auto_play: bool) -> None:
        """Stretch lại bản gốc theo speed hiện tại (thread nền)."""
        if (self._speed_applying or self._busy
                or self._base_waveform is None or self._base_timeline is None):
            return
        speed = self.topbar.get_speed()
        if abs(speed - self._applied_speed) < 1e-9:
            self._speed_dirty = False
            if auto_play and not self._player.is_playing:
                self._player.play()
                self.playback_bar.set_playing(True)
            return
        self._speed_applying = True
        self.topbar.set_status("Đang đổi tốc độ...", theme.TEXT_DIM)
        threading.Thread(
            target=self._speed_worker,
            args=(self._base_waveform, self._base_timeline, speed, auto_play),
            daemon=True,
        ).start()

    def _speed_worker(self, base_wave: np.ndarray, base_timeline: TimelineMap,
                      speed: float, auto_play: bool) -> None:
        try:
            wave = apply_speed(base_wave, speed)
            timeline = base_timeline.scaled(speed)
            self._messages.put(
                ("speed_applied", base_wave, wave, timeline, speed, auto_play))
        except Exception as exc:
            self._messages.put(("speed_apply_error", str(exc)))

    def _start_convert(self) -> None:
        if self._busy:
            return
        text = self.textbox.get_text().strip()
        if not text:
            self.topbar.set_status("Chưa có nội dung để chuyển đổi.", theme.ERROR)
            return
        model = self._selected_model()
        if model is None:
            self.topbar.set_status("Không tìm thấy model giọng đọc.", theme.ERROR)
            return
        speed = self.topbar.get_speed()

        self._player.stop()
        self._waveform = None
        self._timeline = None
        self._synth_text = None
        self._base_waveform = None
        self._base_timeline = None
        self._applied_speed = speed
        self._speed_dirty = False
        self._current_sentence = -1
        self._stream_has_started_playing = False
        self.waveform_timeline.clear()
        self._stop_event.clear()

        self._set_busy(True)
        self.topbar.set_status("Đang chuẩn bị mô hình...", theme.TEXT_DIM)
        threading.Thread(
            target=self._convert_worker, args=(model, text, speed), daemon=True,
        ).start()

    def _stop_convert(self) -> None:
        """Dừng tiến trình tạo âm thanh."""
        if not self._busy:
            return
        self._stop_event.set()
        self.topbar.set_status("Đang dừng...", theme.TEXT_DIM)

    def _convert_worker(self, model, text: str, speed: float) -> None:
        try:
            if self._stop_event.is_set():
                self._messages.put(("stream_stopped",))
                return
            tts = self._model_manager.load_tts(model)
            engine = TtsEngine(tts)
            self._messages.put(("status", "Đang khởi tạo engine...", theme.TEXT_DIM))

            sample_rate = engine.sample_rate
            sentences_count = len(build_sentences(text))
            if sentences_count == 0:
                self._messages.put(("stream_empty",))
                return
            # Luôn sinh bản gốc 1.0x — speed áp bằng time-stretch để giữ bản gốc
            stream_gen = engine.synthesize_stream(text, speed=1.0)

            base_pieces: list[np.ndarray] = []
            base_sentences: list[SentenceItem] = []

            def push_base(timed: SentenceItem, piece: np.ndarray) -> tuple:
                base_pieces.append(piece)
                base_sentences.append(timed)
                piece_out = apply_speed(piece, speed)
                timed_out = SentenceItem(
                    index=timed.index, text=timed.text,
                    char_start=timed.char_start, char_end=timed.char_end,
                    start_sec=timed.start_sec / speed,
                    end_sec=timed.end_sec / speed,
                )
                return timed_out, piece_out

            def post_base() -> None:
                wave = (np.concatenate(base_pieces) if base_pieces
                        else np.zeros(0, dtype=np.float32))
                timeline = TimelineMap(sentences=base_sentences,
                                       sample_rate=sample_rate)
                self._messages.put(("stream_base", wave, timeline, speed))

            # Gửi stream_start ngay (generator nay trễ 1 câu vì lookahead nối pause-pad)
            self._messages.put(("stream_start", sample_rate, sentences_count, text))
            self._messages.put(("status",
                                f"Đang tổng hợp câu 1/{sentences_count}...",
                                theme.TEXT_DIM))
            if self._stop_event.is_set():
                post_base()
                self._messages.put(("stream_stopped",))
                return

            for timed, piece, cur, tot in stream_gen:
                if self._stop_event.is_set():
                    post_base()
                    self._messages.put(("stream_stopped",))
                    return
                timed_out, piece_out = push_base(timed, piece)
                self._messages.put(("stream_chunk", timed_out, piece_out, cur, tot))

            post_base()
            self._messages.put(("stream_end",))
        except Exception as exc:
            self._messages.put(("error", str(exc)))

    # ── Export ──

    def _start_export(self) -> None:
        if self._busy:
            return
        if self._speed_applying:
            self.topbar.set_status(
                "Đang đổi tốc độ — thử xuất lại sau.", theme.TEXT_DIM)
            return
        if self._waveform is None or self._timeline is None:
            self.topbar.set_status("Chưa có âm thanh — hãy chuyển đổi trước.", theme.ERROR)
            return
        path = filedialog.asksaveasfilename(
            title="Xuất file âm thanh",
            defaultextension=".mp3",
            filetypes=[("MP3", "*.mp3"), ("WAV", "*.wav")],
        )
        if not path:
            return
        speed = self.topbar.get_speed()
        self._set_busy(True)
        self.topbar.set_status("Đang xuất file...", theme.TEXT_DIM)
        threading.Thread(target=self._export_worker, args=(path, speed),
                         daemon=True).start()

    def _export_worker(self, path: str, speed: float) -> None:
        try:
            wave = self._waveform
            timeline = self._timeline
            # Speed đã đổi nhưng chưa áp -> stretch bản gốc trước khi xuất
            if (self._speed_dirty and self._base_waveform is not None
                    and abs(speed - self._applied_speed) > 1e-9):
                base_wave = self._base_waveform
                wave = apply_speed(base_wave, speed)
                timeline = self._base_timeline.scaled(speed)
                self._messages.put(
                    ("speed_applied", base_wave, wave, timeline, speed, False))
            out = exporter.export(wave, timeline.sample_rate, path)
            self._messages.put(("exported", str(out)))
        except Exception as exc:
            self._messages.put(("error", str(exc)))

    # ── Playback ──

    def _toggle_play(self) -> None:
        if self._waveform is None:
            self.topbar.set_status("Hãy chuyển đổi văn bản trước.", theme.ERROR)
            return
        if self._player.is_playing or self._player.is_buffering:
            self._player.toggle()
            self.playback_bar.set_playing(self._player.is_playing)
            return
        # Sẽ phát -> áp speed đã đổi (lười) trước, rồi tự phát
        if self._speed_applying:
            self.topbar.set_status("Đang đổi tốc độ...", theme.TEXT_DIM)
            return
        if self._speed_dirty and self._base_waveform is not None:
            self._request_speed_apply(auto_play=True)
            return
        self._player.toggle()
        self.playback_bar.set_playing(self._player.is_playing)

    def _seek(self, seconds: float) -> None:
        if self._waveform is None:
            return
        self._player.seek(seconds)
        self.playback_bar.set_position(self._player.get_position())
        if self._player.is_playing:
            self._highlight_at(seconds)

    def _prev_sentence(self) -> None:
        self._jump_sentence(-1)

    def _next_sentence(self) -> None:
        self._jump_sentence(1)

    def _jump_sentence(self, delta: int) -> None:
        if self._timeline is None or not self._timeline.sentences:
            return
        current = self._timeline.find_index_by_time(self._player.get_position())
        target = max(0, min(current + delta, len(self._timeline.sentences) - 1))
        if current == -1:
            target = 0 if delta > 0 else len(self._timeline.sentences) - 1
        self._seek(self._timeline.sentences[target].start_sec)

    def _on_text_changed(self) -> None:
        if self._synth_text is not None and self.textbox.get_text() != self._synth_text:
            self._invalidate_audio("Văn bản đã thay đổi — hãy chuyển đổi lại.")

    def _invalidate_audio(self, status: str) -> None:
        self._player.stop()
        self._timeline = None
        self._synth_text = None
        self._waveform = None
        self._base_waveform = None
        self._base_timeline = None
        self._speed_dirty = False
        self._current_sentence = -1
        self.textbox.clear_highlight()
        self.playback_bar.set_duration(0.0)
        self.playback_bar.set_playing(False)
        self.waveform_timeline.clear()
        self.topbar.set_status(status, theme.TEXT_DIM)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.topbar.set_busy(busy)

    # ── Message loop ──

    def _drain_messages(self) -> None:
        try:
            while True:
                message = self._messages.get_nowait()
                self._handle_message(message)
        except queue.Empty:
            pass

    def _handle_message(self, message: tuple) -> None:
        kind = message[0]
        if kind == "status":
            _, text, color = message
            self.topbar.set_status(text, color)
        elif kind == "stream_empty":
            self._set_busy(False)
            self.topbar.set_status("Không tìm thấy câu nào hợp lệ.", theme.ERROR)
        elif kind == "stream_start":
            _, sample_rate, total_sentences, text = message
            self._synth_text = text
            self._stream_total_sentences = total_sentences
            self._timeline = TimelineMap(sentences=[], sample_rate=sample_rate)
            self._waveform = np.zeros(0, dtype=np.float32)
            self._player.load(self._waveform, sample_rate, has_more=True)
            self._stream_has_started_playing = False
        elif kind == "stream_chunk":
            _, timed, piece, cur, tot = message
            if self._timeline is None:
                return

            self._timeline.sentences.append(timed)
            if self._waveform is None or len(self._waveform) == 0:
                self._waveform = piece.copy()
            else:
                self._waveform = np.concatenate([self._waveform, piece])

            self._player.append_audio(piece)
            current_duration = len(self._waveform) / self._timeline.sample_rate
            self.playback_bar.set_duration(current_duration)
            self.waveform_timeline.set_audio(
                self._waveform, self._timeline.sample_rate, self._timeline.sentences)

            if not self._stream_has_started_playing:
                if cur >= BUFFER_TRIGGER_SENTENCES or cur == tot:
                    self._stream_has_started_playing = True
                    self._player.play()
                    self.playback_bar.set_playing(True)
                    self.topbar.set_status(
                        f"Đang phát ({cur}/{tot} câu)...", theme.SUCCESS)
                else:
                    self.topbar.set_status(
                        f"Đang đệm câu {cur}/{min(BUFFER_TRIGGER_SENTENCES, tot)}...",
                        theme.TEXT_DIM)
            else:
                if cur < tot:
                    self.topbar.set_status(
                        f"Đang phát... (tạo tiếp câu {cur + 1}/{tot})",
                        theme.TEXT_DIM)

        elif kind == "stream_end":
            self._player.set_has_more(False)
            self._set_busy(False)
            if self._timeline is not None:
                dur = self._timeline.total_duration
                self.playback_bar.set_duration(dur)
                self.topbar.set_status(
                    f"Hoàn tất! {len(self._timeline.sentences)} câu, {dur:.1f} giây.",
                    theme.SUCCESS,
                )
        elif kind == "stream_base":
            _, base_wave, base_timeline, speed = message
            if self._synth_text is None:
                return   # audio đã bị invalidate giữa chừng -> bỏ bản gốc cũ
            self._base_waveform = base_wave
            self._base_timeline = base_timeline
            self._applied_speed = speed
            self._speed_dirty = abs(self.topbar.get_speed() - speed) > 1e-9
        elif kind == "speed_applied":
            _, base_ref, wave, timeline, speed, auto_play = message
            self._speed_applying = False
            if base_ref is not self._base_waveform:
                return   # audio đã bị convert mới/invalidate trong lúc stretch
            old_speed = self._applied_speed
            pos = self._player.get_position()
            was_playing = self._player.is_playing
            sr = timeline.sample_rate

            self._waveform = wave
            self._timeline = timeline
            self._applied_speed = speed
            self._current_sentence = -1

            duration = len(wave) / sr if sr > 0 else 0.0
            new_pos = min(pos * old_speed / speed, duration) if speed > 0 else 0.0
            self._player.load(wave, sr, has_more=False)
            if new_pos > 0:
                self._player.seek(new_pos)
            self.playback_bar.set_duration(duration)
            self.playback_bar.set_position(new_pos)
            self.waveform_timeline.set_audio(wave, sr, timeline.sentences)
            self.waveform_timeline.update_position(new_pos)
            self.textbox.clear_highlight()

            self._speed_dirty = abs(self.topbar.get_speed() - speed) > 1e-9
            should_play = auto_play or was_playing
            if should_play and self._speed_dirty:
                # Đổi speed lần nữa trong lúc stretch -> áp tiếp
                self._request_speed_apply(auto_play=True)
            elif should_play:
                self._player.play()
                self.playback_bar.set_playing(True)
            self.topbar.set_status(f"Đã áp tốc độ {speed:g}x.", theme.SUCCESS)
        elif kind == "speed_apply_error":
            _, text = message
            self._speed_applying = False
            self._speed_dirty = True
            self.topbar.set_status(f"Lỗi đổi tốc độ: {text}", theme.ERROR)
        elif kind == "stream_stopped":
            self._player.stop()
            self._set_busy(False)
            n = len(self._timeline.sentences) if self._timeline else 0
            self.topbar.set_status(
                f"Đã dừng chuyển đổi. Đã tạo {n} câu.", theme.TEXT_DIM)
        elif kind == "exported":
            _, path = message
            self._export_history.append(path)
            self._export_history = self._export_history[-10:]
            self._set_busy(False)
            self.topbar.set_status(f"Đã xuất: {path}", theme.SUCCESS)
        elif kind == "error":
            _, text = message
            self._player.set_has_more(False)
            self._set_busy(False)
            self.topbar.set_status(f"Lỗi: {text}", theme.ERROR)

    def _tick(self) -> None:
        self._drain_messages()
        ended = self._player.update()

        if self._player.is_buffering:
            self.topbar.set_status(
                "Đang chờ tạo thêm âm thanh...", theme.TEXT_DIM)
            self.playback_bar.set_playing(False)
        elif self._player.is_playing:
            self.playback_bar.set_playing(True)
            position = self._player.get_position()
            self.playback_bar.set_position(position)
            self.waveform_timeline.update_position(position)
            self._highlight_at(position)

        if ended:
            self.playback_bar.set_playing(False)
            self.textbox.clear_highlight()
            self.playback_bar.set_position(0.0)
            self.waveform_timeline.update_position(0.0)

        self.after(TICK_MS, self._tick)

    def _highlight_at(self, position: float) -> None:
        if self._timeline is None:
            return
        index = self._timeline.find_index_by_time(position)
        if index == self._current_sentence or index < 0:
            return
        self._current_sentence = index
        sentence = self._timeline.sentences[index]
        self.textbox.highlight_span(sentence.char_start, sentence.char_end)

    def _on_close(self) -> None:
        self._player.quit()
        self.destroy()
