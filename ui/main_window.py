"""Cửa sổ chính của ứng dụng.

Phần tổng hợp/xuất file và phần công cụ (model, cài đặt, trợ giúp) được tách
thành mixin trong gói `ui.window` để mỗi file nằm dưới giới hạn 32 KB của
PyArmor bản miễn phí.
"""

from __future__ import annotations

import queue
import threading
import time

import customtkinter as ctk

import version
from audio.player import AudioPlayer
from audio.temp_store import TempSession, cleanup_stale_sessions
from core.history import HistoryStore
from core.licensing import guard
from core.models import TimelineMap
from core.tags import find_unknown_tags
from engine.model_manager import ModelManager
from ui import theme
from ui.config import load_settings
from ui.components.playback_bar import PlaybackBar
from ui.components.sync_textbox import SyncTextbox
from ui.components.tag_bar import TagBar
from ui.components.topbar import TopBar
from ui.components.waveform_timeline import WaveformTimeline
from ui.window import ConvertMixin, ExportMixin, ToolsMixin

TICK_MS = 40
# Số câu tối thiểu phải có sẵn trong buffer trước khi bắt đầu phát.
# 1 = bắt đầu đọc ngay khi có câu đầu tiên (không đệm 5 câu).
BUFFER_TRIGGER_SENTENCES = 1
# Chu kỳ vẽ lại waveform (giây) — tránh tính lại peaks mỗi câu (O(n²)).
WAVEFORM_REDRAW_SEC = 0.4


class MainWindow(ConvertMixin, ExportMixin, ToolsMixin, ctk.CTk):
    """Điều phối: TopBar ↔ Textbox ↔ PlaybackBar ↔ TTS Engine.

    Kiến trúc âm thanh:
      - _base_store : audio gốc 1.0x (RAM hoặc file tạm)
      - _play_store : audio đã áp tốc độ (alias base_store khi speed = 1.0)
    Cả hai đều là "source" (total_samples + read) nên player và timeline
    dùng chung được, không copy dữ liệu.
    """

    def __init__(self) -> None:
        super().__init__()
        self.title(f"{version.__app_name__} - v{version.__version__}")
        self.geometry("1200x740")
        self.minsize(980, 600)
        ctk.set_appearance_mode("light")
        self.configure(fg_color=theme.BG)

        self._settings = load_settings()
        self._model_manager = ModelManager(
            precision=self._settings["precision"],
            threads=self._settings["threads"],
        )
        self._history = HistoryStore()
        self._player = AudioPlayer()
        self._messages: queue.Queue = queue.Queue()
        self._worker: threading.Thread | None = None
        self._busy = False
        self._stop_event = threading.Event()

        # Dọn file audio tạm còn sót từ lần chạy trước bị tắt đột ngột.
        try:
            from core.paths import data_dir

            cleanup_stale_sessions(data_dir() / "tmp")
        except Exception:
            pass

        # ── Nguồn âm thanh ──
        self._base_store = None          # source 1.0x
        self._play_store = None          # source đã áp speed
        self._base_spans: list[tuple[int, int]] = []   # (start, end) mẫu trong base
        self._sample_rate = 48000
        self._disk_mode = False
        self._temp_session: TempSession | None = None
        self._store_seq = 0

        self._timeline: TimelineMap | None = None        # timeline của play
        self._base_timeline: TimelineMap | None = None   # timeline của base
        self._synth_text: str | None = None
        self._applied_speed: float = 1.0     # speed của _play_store hiện tại
        self._speed_dirty: bool = False      # speed đã đổi nhưng chưa áp
        self._speed_applying: bool = False   # guard thread đổi speed
        self._current_sentence = -1
        self._stream_total_sentences = 0
        self._stream_has_started_playing = False
        self._last_waveform_draw = 0.0

        self._all_models: list = []
        self._export_history: list[str] = []
        self._warned_device = False
        self._last_license_check = 0.0

        self._build_ui()
        self._refresh_license_badge()
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
            on_merge=self._open_merge_dialog,
            on_settings=self._open_settings,
            on_history=self._open_history,
            on_help=self._open_help,
            on_about=self._show_about,
            on_license=self._open_license_dialog,
            on_close=self._on_close,
        )
        self.topbar.grid(row=0, column=0, sticky="ew")

        # ── Main area (full-width) ──
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 14))
        main.grid_rowconfigure(0, weight=0)
        main.grid_rowconfigure(1, weight=1)
        main.grid_rowconfigure(2, weight=0)
        main.grid_rowconfigure(3, weight=0)
        main.grid_columnconfigure(0, weight=1)

        self.tag_bar = TagBar(main, on_insert=self._insert_tag)
        self.tag_bar.grid(row=0, column=0, sticky="ew", pady=(0, 4))

        self.textbox = SyncTextbox(main, on_text_changed=self._on_text_changed)
        self.textbox.grid(row=1, column=0, sticky="nsew")

        self.waveform_timeline = WaveformTimeline(main)
        self.waveform_timeline.grid(row=2, column=0, sticky="ew", pady=(6, 0))

        self.playback_bar = PlaybackBar(
            main,
            on_toggle=self._toggle_play,
            on_seek=self._seek,
            on_prev_sentence=self._prev_sentence,
            on_next_sentence=self._next_sentence,
        )
        self.playback_bar.grid(row=3, column=0, sticky="ew", pady=(6, 0))

    # ── Bản quyền ──

    def _refresh_license_badge(self, status=None):
        """Cập nhật nhãn 🔑 trên thanh menu theo trạng thái hiện tại."""
        status = status or guard.check_startup(use_cache=False)
        color = theme.TEXT_DIM
        left = status.days_left
        if not status.active:
            color = theme.ERROR
        elif left is not None and left <= 1:
            color = theme.ERROR
        elif left is not None and left <= 7:
            color = "#b7791f"
        self.topbar.set_license(status.badge_text(), color)
        return status

    def _open_license_dialog(self) -> None:
        from ui.components.license_dialog import LicenseDialog

        LicenseDialog(self, on_activate=self._open_activation)
        self._refresh_license_badge()

    def _open_activation(self) -> bool:
        from ui.components.activation_dialog import ask_activation

        ok = ask_activation(self, status=guard.check_startup(use_cache=False))
        self._refresh_license_badge()
        if ok and not self._all_models:
            self._scan_models()
        return ok

    def _ensure_license(self) -> bool:
        """Chặn thao tác khi chưa kích hoạt/hết hạn; mở hộp thoại nếu cần."""
        status = guard.check_startup(use_cache=False)
        if status.active:
            return True
        self._refresh_license_badge(status)
        self.topbar.set_status(
            status.message or "Thiết bị chưa được kích hoạt.", theme.ERROR)
        return self._open_activation()

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
        if self._base_store is None or self._play_store is None:
            return
        self._speed_dirty = True
        if self._player.is_playing:
            # Đang phát -> áp ngay, giữ vị trí, phát tiếp không gián đoạn
            self._request_speed_apply(auto_play=False)
        else:
            self.topbar.set_status(
                "Đã đổi tốc độ — bấm Phát để áp dụng.", theme.TEXT_DIM)

    # ── Playback ──

    def _toggle_play(self) -> None:
        if self._play_store is None:
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
        if self._speed_dirty and self._base_store is not None:
            self._request_speed_apply(auto_play=True)
            return
        self._player.toggle()
        self.playback_bar.set_playing(self._player.is_playing)

    def _seek(self, seconds: float) -> None:
        if self._play_store is None:
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

    def _insert_tag(self, tag: str) -> None:
        """Chèn thẻ điều khiển vào khung soạn thảo tại con trỏ."""
        self.textbox.insert_at_cursor(tag)
        self.textbox.focus_set()

    def _on_text_changed(self) -> None:
        if self._synth_text is not None and self.textbox.get_text() != self._synth_text:
            self._invalidate_audio("Văn bản đã thay đổi - hãy chuyển đổi lại.")
        self._refresh_tag_hint()

    def _refresh_tag_hint(self) -> None:
        """Cảnh báo ngay trên thanh chèn nhanh nếu có thẻ chưa hỗ trợ."""
        unknown = find_unknown_tags(self.textbox.get_text())
        if not unknown:
            self.tag_bar.set_hint(None)
            return
        preview = ", ".join(unknown[:3])
        if len(unknown) > 3:
            preview += f" (+{len(unknown) - 3})"
        self.tag_bar.set_hint(f"Thẻ chưa hỗ trợ (sẽ đọc thành chữ): {preview}",
                              error=True)

    def _invalidate_audio(self, status: str) -> None:
        self._player.stop()
        self._release_stores()
        self._synth_text = None
        self._speed_dirty = False
        self._current_sentence = -1
        self.textbox.clear_highlight()
        self.playback_bar.set_duration(0.0)
        self.playback_bar.set_playing(False)
        self.waveform_timeline.clear()
        self.topbar.set_status(status, theme.TEXT_DIM)

    def _release_stores(self) -> None:
        """Giải phóng store (RAM + file tạm) và reset timeline."""
        for store in (self._play_store, self._base_store):
            if store is None:
                continue
            cleanup = getattr(store, "cleanup", None)
            if cleanup is not None:
                try:
                    cleanup()
                except Exception:
                    pass
        self._base_store = None
        self._play_store = None
        self._base_spans = []
        self._timeline = None
        self._base_timeline = None
        if self._temp_session is not None:
            self._temp_session.cleanup()
            self._temp_session = None

    def _maybe_apply_pending_speed(self) -> None:
        """Áp tốc độ còn treo (đổi trong lúc đang chuyển đổi) sau khi xong."""
        if not self._speed_dirty or self._speed_applying:
            return
        if self._base_store is None or self._base_timeline is None:
            return
        if abs(self.topbar.get_speed() - self._applied_speed) < 1e-9:
            self._speed_dirty = False
            return
        self._request_speed_apply(auto_play=False)

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
        elif kind == "stream_chunk":
            _, timed, cur, tot = message
            if self._timeline is None:
                return

            self._timeline.sentences.append(timed)
            if self._base_timeline is not None and self._base_timeline is not self._timeline:
                self._base_timeline.sentences.append(timed)

            current_duration = self._play_store.total_samples / self._sample_rate
            self.playback_bar.set_duration(current_duration)

            now = time.monotonic()
            if now - self._last_waveform_draw >= WAVEFORM_REDRAW_SEC:
                self._last_waveform_draw = now
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

    def _tick(self) -> None:
        self._drain_messages()
        ended = self._player.update()

        # Mỗi phút: ghi mốc thời gian + kiểm tra lại bản quyền (hết hạn giữa phiên).
        now = time.time()
        if now - self._last_license_check >= 60:
            self._last_license_check = now
            status = guard.record_activity(now)
            self._refresh_license_badge(status)
            if not status.active:
                if self._busy:
                    self._stop_event.set()
                self.topbar.set_status(
                    status.message or "Bản quyền không hợp lệ.", theme.ERROR)

        if not self._player.available and not self._warned_device:
            self._warned_device = True
            self.topbar.set_status(
                "Không mở được thiết bị phát âm thanh — vẫn xuất file được.",
                theme.ERROR)

        if self._player.is_buffering:
            # Chỉ báo "đang chờ" khi còn audio đang được tạo — tránh ghi đè
            # thông báo "Hoàn tất!" khi playback đã kết thúc.
            if self._busy or self._player.has_more:
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
        self._release_stores()
        self.destroy()
