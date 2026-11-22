from __future__ import annotations

import threading

import numpy as np

from audio.buffer import GrowableBuffer
from audio.speed import apply_speed
from audio.temp_store import TempSession, should_use_disk
from core.models import SentenceItem, TimelineMap
from core.text_processor import build_sentences
from engine.tts_engine import TtsEngine
from ui import theme


class ConvertMixin:
    """Tổng hợp giọng nói + áp tốc độ.

    Mixin thuần: không định nghĩa __init__, dùng chung state với MainWindow
    (`_messages`, `_stop_event`, `_base_store`, `_play_store`, ...).
    """

    # ── Convert ──

    def _request_speed_apply(self, auto_play: bool) -> None:
        """Dựng lại audio theo speed hiện tại (thread nền)."""
        if (self._speed_applying or self._busy
                or self._base_store is None or self._base_timeline is None):
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
            target=self._speed_worker, args=(speed, auto_play), daemon=True,
        ).start()

    def _speed_worker(self, speed: float, auto_play: bool) -> None:
        try:
            store, timeline = self._build_play_store(speed)
            self._messages.put(("speed_applied", store, timeline, speed, auto_play))
        except Exception as exc:
            self._messages.put(("speed_apply_error", str(exc)))

    # ── Store ──

    def _new_store(self, name: str):
        """Tạo store mới theo chế độ lưu hiện tại (RAM hay file tạm).

        Tên file có số thứ tự để mỗi lần dựng lại (đổi tốc độ) tạo file
        riêng — tránh ghi đè file mà store cũ còn đang đọc.
        """
        self._store_seq += 1
        unique = f"{name}{self._store_seq}"
        if self._disk_mode:
            if self._temp_session is None:
                from core.paths import data_dir

                self._temp_session = TempSession(data_dir() / "tmp")
            return self._temp_session.store(unique, self._sample_rate)
        return GrowableBuffer()

    def _build_play_store(self, speed: float):
        """Dựng lại audio đã áp tốc độ từ audio gốc 1.0x.

        Trả về (store, timeline). Với speed = 1.0 -> dùng luôn store gốc
        (alias, không tốn thêm RAM/disk).
        """
        base = self._base_store
        base_timeline = self._base_timeline
        if base is None or base_timeline is None:
            return None, None
        if abs(speed - 1.0) < 1e-9:
            return base, base_timeline

        new_store = self._new_store("play")
        for start, end in self._base_spans:
            piece = base.read(start, end - start)
            if piece is None or piece.size == 0:
                continue
            # Copy để không đụng vào buffer gốc (time-stretch có thể ghi tại chỗ).
            new_store.append(apply_speed(np.array(piece, dtype=np.float32), speed))
        timeline = base_timeline.scaled(speed)
        return new_store, timeline

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
        self._release_stores()
        self._synth_text = None
        self._applied_speed = speed
        self._speed_dirty = False
        self._text_dirty = False
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

            # Chế độ lưu: bài ngắn giữ trong RAM, bài dài ghi ra file tạm.
            disk = should_use_disk(text, self._settings.get("storage", "auto"))
            self._disk_mode = disk
            self._sample_rate = sample_rate
            base_store = self._new_store("base")
            play_store = base_store if abs(speed - 1.0) < 1e-9 else self._new_store("play")

            # Luôn sinh bản gốc 1.0x — speed áp bằng time-stretch để giữ bản gốc
            stream_gen = engine.synthesize_stream(text, speed=1.0)
            base_spans: list[tuple[int, int]] = []
            base_sentences: list[SentenceItem] = []

            # Gửi stream_init ngay (generator không còn lookahead)
            self._messages.put(("stream_init", sample_rate, sentences_count, text,
                                base_store, play_store, disk))
            self._messages.put(("status",
                                f"Đang tổng hợp câu 1/{sentences_count}...",
                                theme.TEXT_DIM))
            if self._stop_event.is_set():
                self._messages.put(("stream_stopped",))
                return

            for timed, piece, cur, tot in stream_gen:
                if self._stop_event.is_set():
                    break
                start_sample = base_store.total_samples
                base_store.append(piece)
                base_spans.append((start_sample, base_store.total_samples))
                base_sentences.append(timed)
                if play_store is not base_store:
                    play_store.append(apply_speed(piece, speed))
                timed_out = SentenceItem(
                    index=timed.index, text=timed.text,
                    char_start=timed.char_start, char_end=timed.char_end,
                    start_sec=timed.start_sec / speed,
                    end_sec=timed.end_sec / speed,
                )
                self._messages.put(("stream_chunk", timed_out, cur, tot))

            base_timeline = TimelineMap(sentences=base_sentences,
                                        sample_rate=sample_rate)
            play_timeline = (base_timeline if abs(speed - 1.0) < 1e-9
                             else base_timeline.scaled(speed))
            self._messages.put(("stream_base", base_spans, base_timeline,
                                play_timeline, speed))
            if self._stop_event.is_set():
                self._messages.put(("stream_stopped",))
                return
            self._messages.put(("stream_end",))
        except Exception as exc:
            self._messages.put(("error", str(exc)))
