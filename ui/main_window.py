from __future__ import annotations

import queue
import threading
from tkinter import filedialog

import customtkinter as ctk
import numpy as np

import version
from audio import exporter
from audio.player import AudioPlayer
from core.models import TimelineMap
from engine.model_manager import ModelManager
from engine.tts_engine import TtsEngine
from ui import theme
from ui.config import load_enabled_voices, save_enabled_voices
from ui.components.sidebar import Sidebar
from ui.components.playback_bar import PlaybackBar
from ui.components.sync_textbox import SyncTextbox
from ui.components.voice_manager import VoiceManagerDialog
from ui.components.waveform_timeline import WaveformTimeline

TICK_MS = 40
BUFFER_TRIGGER_SENTENCES = 5


class MainWindow(ctk.CTk):
    """Điều phối: Sidebar ↔ Textbox ↔ PlaybackBar ↔ TTS Engine."""

    def __init__(self) -> None:
        super().__init__()
        self.title(f"{version.__app_name__} - v{version.__version__}")
        self.geometry("1100x720")
        self.minsize(860, 560)
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
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ── Sidebar (trái) ──
        self.sidebar = Sidebar(
            self,
            on_open_file=self._open_file,
            on_voice_change=self._on_voice_change,
            on_speed_change=self._on_speed_change,
            on_convert=self._start_convert,
            on_stop=self._stop_convert,
            on_export=self._start_export,
            on_manage_voices=self._open_voice_manager,
            on_test_voice=self._test_voice,
            on_merge=self._open_merge_dialog,
        )
        self.sidebar.grid(row=0, column=0, sticky="nsw")

        # ── Main area (phải) ──
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew", padx=(0, 14), pady=14)
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

    def _scan_models(self) -> None:
        self._all_models = self._model_manager.scan()
        if not self._all_models:
            self.sidebar.set_status(
                "Không tìm thấy mô hình — chạy download_model.py",
                theme.ERROR,
            )
            return

        enabled = load_enabled_voices()
        if enabled is not None:
            visible = [m for m in self._all_models if m.model_id in enabled]
        else:
            visible = self._all_models

        if not visible:
            self.sidebar.set_voices([], None)
            self.sidebar.set_status(
                "Tất cả giọng đều bị tắt — bấm ＋ Thêm để bật lại.", theme.ERROR)
            return

        names = [m.display_name for m in visible]
        self.sidebar.set_voices(names, names[0])
        self.sidebar.set_status(
            f"{len(names)}/{len(self._all_models)} giọng sẵn sàng.", theme.TEXT_DIM)

    def _selected_model(self):
        name = self.sidebar.get_selected_voice()
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

        VoiceManagerDialog(self, self._all_models, enabled, on_save)

    def _open_merge_dialog(self) -> None:
        from ui.components.merge_dialog import MergeDialog

        MergeDialog(
            self,
            export_history=self._export_history,
            on_merged=lambda path: self.sidebar.set_status(
                f"Đã ghép: {path}", theme.SUCCESS),
        )

    # ── Test giọng ──

    def _test_voice(self) -> None:
        model = self._selected_model()
        if model is None:
            self.sidebar.set_status("Không có giọng để test.", theme.ERROR)
            return
        test_text = self.sidebar.get_test_text()
        speed = self.sidebar.get_speed()
        self.sidebar.set_status(f"Đang nạp {model.display_name}...", theme.TEXT_DIM)
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
            self.sidebar.set_status(f"Đã mở: {path}", theme.SUCCESS)
        except Exception as exc:
            self.sidebar.set_status(f"Không mở được file: {exc}", theme.ERROR)

    # ── Callbacks từ sidebar ──

    def _on_voice_change(self, _value: str) -> None:
        if self._synth_text is not None:
            self.sidebar.set_status(
                "Đã đổi giọng — bấm Chuyển đổi để áp dụng.", theme.TEXT_DIM)

    def _on_speed_change(self, _value: float) -> None:
        if self._synth_text is not None:
            self.sidebar.set_status(
                "Đã đổi tốc độ — bấm Chuyển đổi để áp dụng.", theme.TEXT_DIM)

    # ── Convert ──

    def _start_convert(self) -> None:
        if self._busy:
            return
        text = self.textbox.get_text().strip()
        if not text:
            self.sidebar.set_status("Chưa có nội dung để chuyển đổi.", theme.ERROR)
            return
        model = self._selected_model()
        if model is None:
            self.sidebar.set_status("Không tìm thấy model giọng đọc.", theme.ERROR)
            return
        speed = self.sidebar.get_speed()

        self._player.stop()
        self._waveform = None
        self._timeline = None
        self._synth_text = None
        self._current_sentence = -1
        self._stream_has_started_playing = False
        self.waveform_timeline.clear()
        self._stop_event.clear()

        self._set_busy(True)
        self.sidebar.set_status("Đang chuẩn bị mô hình...", theme.TEXT_DIM)
        threading.Thread(
            target=self._convert_worker, args=(model, text, speed), daemon=True,
        ).start()

    def _stop_convert(self) -> None:
        """Dừng tiến trình tạo âm thanh."""
        if not self._busy:
            return
        self._stop_event.set()
        self.sidebar.set_status("Đang dừng...", theme.TEXT_DIM)

    def _convert_worker(self, model, text: str, speed: float) -> None:
        try:
            if self._stop_event.is_set():
                self._messages.put(("stream_stopped",))
                return
            tts = self._model_manager.load_tts(model)
            engine = TtsEngine(tts)
            self._messages.put(("status", "Đang khởi tạo engine...", theme.TEXT_DIM))

            sample_rate = engine.sample_rate
            stream_gen = engine.synthesize_stream(text, speed=speed)

            first_item = next(stream_gen, None)
            if first_item is None:
                self._messages.put(("stream_empty",))
                return
            if self._stop_event.is_set():
                self._messages.put(("stream_stopped",))
                return

            timed, piece, cur, tot = first_item
            self._messages.put(("stream_start", sample_rate, tot, text))
            self._messages.put(("stream_chunk", timed, piece, cur, tot))

            for timed, piece, cur, tot in stream_gen:
                if self._stop_event.is_set():
                    self._messages.put(("stream_stopped",))
                    return
                self._messages.put(("stream_chunk", timed, piece, cur, tot))

            self._messages.put(("stream_end",))
        except Exception as exc:
            self._messages.put(("error", str(exc)))

    # ── Export ──

    def _start_export(self) -> None:
        if self._busy:
            return
        if self._waveform is None or self._timeline is None:
            self.sidebar.set_status("Chưa có âm thanh — hãy chuyển đổi trước.", theme.ERROR)
            return
        path = filedialog.asksaveasfilename(
            title="Xuất file âm thanh",
            defaultextension=".mp3",
            filetypes=[("MP3", "*.mp3"), ("WAV", "*.wav")],
        )
        if not path:
            return
        self._set_busy(True)
        self.sidebar.set_status("Đang xuất file...", theme.TEXT_DIM)
        threading.Thread(target=self._export_worker, args=(path,), daemon=True).start()

    def _export_worker(self, path: str) -> None:
        try:
            out = exporter.export(self._waveform, self._timeline.sample_rate, path)
            self._messages.put(("exported", str(out)))
        except Exception as exc:
            self._messages.put(("error", str(exc)))

    # ── Playback ──

    def _toggle_play(self) -> None:
        if self._waveform is None:
            self.sidebar.set_status("Hãy chuyển đổi văn bản trước.", theme.ERROR)
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
        self._current_sentence = -1
        self.textbox.clear_highlight()
        self.playback_bar.set_duration(0.0)
        self.playback_bar.set_playing(False)
        self.waveform_timeline.clear()
        self.sidebar.set_status(status, theme.TEXT_DIM)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.sidebar.set_busy(busy)

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
            self.sidebar.set_status(text, color)
        elif kind == "stream_empty":
            self._set_busy(False)
            self.sidebar.set_status("Không tìm thấy câu nào hợp lệ.", theme.ERROR)
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
                    self.sidebar.set_status(
                        f"Đang phát ({cur}/{tot} câu)...", theme.SUCCESS)
                else:
                    self.sidebar.set_status(
                        f"Đang đệm câu {cur}/{min(BUFFER_TRIGGER_SENTENCES, tot)}...",
                        theme.TEXT_DIM)
            else:
                if cur < tot:
                    self.sidebar.set_status(
                        f"Đang phát... (tạo tiếp câu {cur + 1}/{tot})",
                        theme.TEXT_DIM)

        elif kind == "stream_end":
            self._player.set_has_more(False)
            self._set_busy(False)
            if self._timeline is not None:
                dur = self._timeline.total_duration
                self.playback_bar.set_duration(dur)
                self.sidebar.set_status(
                    f"Hoàn tất! {len(self._timeline.sentences)} câu, {dur:.1f} giây.",
                    theme.SUCCESS,
                )
        elif kind == "stream_stopped":
            self._player.stop()
            self._set_busy(False)
            n = len(self._timeline.sentences) if self._timeline else 0
            self.sidebar.set_status(
                f"Đã dừng chuyển đổi. Đã tạo {n} câu.", theme.TEXT_DIM)
        elif kind == "exported":
            _, path = message
            self._export_history.append(path)
            self._export_history = self._export_history[-10:]
            self._set_busy(False)
            self.sidebar.set_status(f"Đã xuất: {path}", theme.SUCCESS)
        elif kind == "error":
            _, text = message
            self._player.set_has_more(False)
            self._set_busy(False)
            self.sidebar.set_status(f"Lỗi: {text}", theme.ERROR)

    def _tick(self) -> None:
        self._drain_messages()
        ended = self._player.update()

        if self._player.is_buffering:
            self.sidebar.set_status(
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
