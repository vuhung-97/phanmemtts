"""Vòng lặp message + các hằng số liên quan của MainWindow.

Tách khỏi main_window.py để giữ mỗi file dưới giới hạn 32 KB của PyArmor.
"""

from __future__ import annotations

import queue
import time

from core.models import TimelineMap
from ui import theme

# Số câu tối thiểu phải có sẵn trong buffer trước khi bắt đầu phát.
BUFFER_TRIGGER_SENTENCES = 1
# Chu kỳ vẽ lại waveform (giây) — tránh tính lại peaks mỗi câu (O(n²)).
WAVEFORM_REDRAW_SEC = 1.0
# Chỉ vẽ lại khi audio tăng thêm ít nhất 5% (tránh quét lại liên tục).
WAVEFORM_GROWTH_RATIO = 0.05


class MessagesMixin:
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
        elif kind == "stream_init":
            (_, sample_rate, total_sentences, text,
             base_store, play_store, disk) = message
            self._synth_text = text
            self._stream_total_sentences = total_sentences
            self._sample_rate = sample_rate
            self._base_store = base_store
            self._play_store = play_store
            self._disk_mode = disk
            self._base_spans = []
            self._timeline = TimelineMap(sentences=[], sample_rate=sample_rate)
            self._base_timeline = self._timeline
            self._player.load_source(play_store, sample_rate, has_more=True)
            self._stream_has_started_playing = False
            self._last_waveform_draw = 0.0
            self._last_waveform_samples = 0
            self.shell.player_bar.set_transport_enabled(True)
        elif kind == "stream_chunk":
            _, timed, cur, tot = message
            if self._timeline is None:
                return

            self._timeline.sentences.append(timed)
            if self._base_timeline is not None and self._base_timeline is not self._timeline:
                self._base_timeline.sentences.append(timed)

            total_samples = self._play_store.total_samples
            current_duration = total_samples / self._sample_rate
            self.playback_bar.set_duration(current_duration)

            now = time.monotonic()
            grown = (self._last_waveform_samples == 0
                     or total_samples
                     >= self._last_waveform_samples * (1 + WAVEFORM_GROWTH_RATIO))
            if grown and now - self._last_waveform_draw >= WAVEFORM_REDRAW_SEC:
                self._last_waveform_draw = now
                self._last_waveform_samples = total_samples
                self.waveform_timeline.set_source(
                    self._play_store, self._sample_rate, self._timeline.sentences)

            if not self._stream_has_started_playing:
                if cur >= BUFFER_TRIGGER_SENTENCES or cur == tot:
                    self._stream_has_started_playing = True
                    self._player.play()
                    self.playback_bar.set_playing(True)
                    self.topbar.set_status(
                        f"Đang phát ({cur}/{tot} câu)...", theme.SUCCESS)
                else:
                    self.topbar.set_status(
                        f"Đang đệm câu {cur}...",
                        theme.TEXT_DIM)
            else:
                if cur < tot:
                    self.topbar.set_status(
                        f"Đang phát... (tạo tiếp câu {cur + 1}/{tot})",
                        theme.TEXT_DIM)

        elif kind == "stream_base":
            _, base_spans, base_timeline, play_timeline, speed = message
            self._base_spans = base_spans
            self._base_timeline = base_timeline
            self._timeline = play_timeline
            self._applied_speed = speed
            self._speed_dirty = abs(self.topbar.get_speed() - speed) > 1e-9
            self.waveform_timeline.set_source(
                self._play_store, self._sample_rate, play_timeline.sentences)
        elif kind == "stream_end":
            self._player.set_has_more(False)
            self._set_busy(False)
            if self._text_dirty:
                self._text_dirty = False
                if (self._synth_text is not None
                        and self.textbox.get_text() != self._synth_text):
                    self._invalidate_audio(
                        "Văn bản đã thay đổi - hãy chuyển đổi lại.")
                    return
            if self._timeline is not None:
                dur = self._timeline.total_duration
                self.playback_bar.set_duration(dur)
                self.topbar.set_status(
                    f"Hoàn tất! {len(self._timeline.sentences)} câu, {dur:.1f} giây.",
                    theme.SUCCESS,
                )
            # Đổi tốc độ trong lúc đang chuyển đổi -> áp ngay bây giờ.
            self._maybe_apply_pending_speed()
        elif kind == "speed_applied":
            _, store, timeline, speed, auto_play = message
            self._speed_applying = False
            if store is None:
                return
            old_speed = self._applied_speed
            pos = self._player.get_position()
            was_playing = self._player.is_playing
            sr = timeline.sample_rate

            # Thay store play (giải phóng bản cũ nếu khác và không phải bản gốc)
            old_store = self._play_store
            self._play_store = store
            self._timeline = timeline
            self._applied_speed = speed
            self._current_sentence = -1
            if old_store is not None and old_store is not store \
                    and old_store is not self._base_store:
                cleanup = getattr(old_store, "cleanup", None)
                if cleanup is not None:
                    try:
                        cleanup()
                    except Exception:
                        pass

            duration = store.total_samples / sr if sr > 0 else 0.0
            new_pos = min(pos * old_speed / speed, duration) if speed > 0 else 0.0
            self._player.load_source(store, sr, has_more=False)
            if new_pos > 0:
                self._player.seek(new_pos)
            self.playback_bar.set_duration(duration)
            self.playback_bar.set_position(new_pos)
            self.waveform_timeline.set_source(store, sr, timeline.sentences)
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
            self._maybe_apply_pending_speed()
        elif kind == "exported":
            _, path = message
            self._export_history.append(path)
            self._export_history = self._export_history[-10:]
            self._set_busy(False)
            self.topbar.set_status(f"Đã xuất: {path}", theme.SUCCESS)
        elif kind == "license_blocked":
            _, text = message
            self._set_busy(False)
            self.topbar.set_status(text, theme.ERROR)
            self._refresh_license_badge()
        elif kind == "error":
            _, text = message
            self._player.set_has_more(False)
            self._set_busy(False)
            self.topbar.set_status(f"Lỗi: {text}", theme.ERROR)

