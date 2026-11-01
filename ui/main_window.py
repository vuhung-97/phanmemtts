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
from ui.pages.dictionary_page import DictionaryPage
from ui.pages.license_page import LicensePage
from ui.pages.placeholder_page import PlaceholderPage
from ui.pages.settings_page import SettingsPage
from ui.pages.text_page import TextPage
from ui.pages.voices_page import VoicesPage
from ui.shell.app_shell import AppShell
from ui.window import (ConvertMixin, ExportMixin, LicenseMixin,
                       MessagesMixin, ToolsMixin)

TICK_MS = 40


class MainWindow(ConvertMixin, ExportMixin, LicenseMixin, MessagesMixin,
                 ToolsMixin, ctk.CTk):
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
        self.geometry("1280x800")
        self.minsize(1024, 700)
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
        self._last_license_state = ""

        self._build_ui()
        self._refresh_license_badge()
        self._prompt_job = self.after(400, self._first_run_prompt)
        self._scan_models()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(TICK_MS, self._tick)

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.shell = AppShell(
            self,
            app_name=version.__app_name__,
            version=version.__version__,
            toolbar_callbacks={
                "open_file": self._open_file,
                "help": self._open_help,
                "terms": self._open_terms,
                "license": self._open_license_dialog,
                "about": self._show_about,
                "close": self._on_close,
            },
            on_navigate=self._navigate,
            player_callbacks={
                "toggle": self._toggle_play,
                "seek": self._seek,
                "prev": self._prev_sentence,
                "next": self._next_sentence,
                "speed": self._on_speed_change,
            },
        )
        self.shell.grid(row=0, column=0, sticky="nsew")

        self.text_page = TextPage(self.shell.content, self)
        self.shell.register(self.text_page)
        self.settings_page = SettingsPage(self.shell.content, self)
        self.shell.register(self.settings_page)
        self.license_page = LicensePage(self.shell.content, self)
        self.shell.register(self.license_page)
        self.dictionary_page = DictionaryPage(self.shell.content, self)
        self.shell.register(self.dictionary_page)
        self.voices_page = VoicesPage(self.shell.content, self)
        self.shell.register(self.voices_page)
        self.shell.register(PlaceholderPage(
            self.shell.content, self, page_id="dialogue", title="Hội thoại",
            note="Hội thoại nhiều giọng sẽ có ở bước P4 của kế hoạch 3.5.0."))

        # ── Alias tương thích mixin/probe cũ ──
        self.topbar = self.text_page
        self.textbox = self.text_page.editor
        self.tag_bar = self.text_page.tag_bar
        self.playback_bar = self.shell.player_bar
        self.waveform_timeline = self.shell.player_bar.waveform

        self.shell.show("text")
        self.shell.player_bar.set_visible(False)

        self.bind("<Control-h>", lambda _e: self._navigate("history"))
        self.bind("<Control-b>", lambda _e: self._navigate("batch"))

    # ── Điều hướng sidebar ──

    def _navigate(self, page_id: str) -> None:
        """Mở page mới; chức năng chưa port thì mở dialog cũ (P0)."""
        if self.shell.show(page_id):
            return
        legacy = {
            "merge": self._open_merge_dialog,
            "batch": self._open_batch_dialog,
            "history": self._open_history,
            "dictionary": self._open_dictionary,
            "voices": self._open_voice_manager,
            "settings": self._open_settings,
            "license": self._open_license_dialog,
        }
        handler = legacy.get(page_id)
        if handler is not None:
            handler()
        current = self.shell.current_page
        if current is not None:
            self.shell.sidebar.set_active(current.page_id)

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
        if hasattr(self, "shell"):
            self.shell.player_bar.clear()
            self.shell.player_bar.set_visible(False)
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
        if hasattr(self, "shell"):
            self.shell.set_busy(busy)
        self.topbar.set_busy(busy)

    def _tick(self) -> None:
        self._drain_messages()
        ended = self._player.update()

        # Mỗi phút: ghi mốc thời gian + kiểm tra lại bản quyền.
        # Chưa kích hoạt KHÔNG dừng chuyển đổi (vẫn nghe thử được), chỉ khoá xuất file.
        now = time.time()
        if now - self._last_license_check >= 60:
            self._last_license_check = now
            status = guard.record_activity(now)
            self._refresh_license_badge(status)
            if status.state != self._last_license_state:
                self._last_license_state = status.state
                if not status.active and not self._busy:
                    self.topbar.set_status(
                        status.message or "Cần mã kích hoạt để xuất file.",
                        theme.TEXT_DIM)

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
