from __future__ import annotations

import threading
from tkinter import filedialog

from audio import exporter
from ui import theme


class ExportMixin:
    """Xuất file âm thanh và ghi lịch sử bản dựng."""

    # ── Export ──

    def _start_export(self) -> None:
        if self._busy:
            return
        if self._speed_applying:
            self.topbar.set_status(
                "Đang đổi tốc độ — thử xuất lại sau.", theme.TEXT_DIM)
            return
        if self._play_store is None or self._timeline is None:
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
        voice = self.topbar.get_selected_voice()
        self._set_busy(True)
        self.topbar.set_status("Đang xuất file...", theme.TEXT_DIM)
        threading.Thread(target=self._export_worker, args=(path, speed, voice),
                         daemon=True).start()

    def _export_worker(self, path: str, speed: float, voice: str) -> None:
        try:
            store = self._play_store
            timeline = self._timeline
            # Speed đã đổi nhưng chưa áp -> dựng lại audio theo speed mới
            if self._speed_dirty and abs(speed - self._applied_speed) > 1e-9:
                new_store, new_timeline = self._build_play_store(speed)
                if new_store is not None:
                    store, timeline = new_store, new_timeline
                    self._messages.put(
                        ("speed_applied", new_store, new_timeline, speed, False))
            out = exporter.export_source(store, timeline.sample_rate, path)
            self._record_history(path, speed, voice)
            self._messages.put(("exported", str(out)))
        except Exception as exc:
            self._messages.put(("error", str(exc)))

    def _record_history(self, path: str, speed: float, voice: str) -> None:
        """Ghi lịch sử bản dựng; lỗi lịch sử không được làm hỏng luồng xuất."""
        try:
            timeline = self._timeline
            duration = 0.0
            if timeline is not None and timeline.sentences:
                duration = float(timeline.sentences[-1].end_sec)
            text = self._synth_text or ""
            self._history.add(
                path,
                voice=voice,
                speed=speed,
                duration=duration,
                chars=len(text),
                preview=text,
            )
        except Exception:
            pass
