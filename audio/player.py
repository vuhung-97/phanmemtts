from __future__ import annotations

import threading
from enum import Enum

import numpy as np
import sounddevice as sd


class PlayerState(Enum):
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    BUFFERING = "buffering"
    STOPPED = "stopped"


class AudioPlayer:
    """Phát âm thanh bằng stream liên tục (sounddevice):

    - Hỗ trợ append_audio() gối đầu động
    - Tự động chuyển BUFFERING khi đệm trống mà chưa xong (has_more=True)
    - Tự động phát tiếp ngay khi có audio mới nạp vào
    """

    def __init__(self) -> None:
        self._waveform: np.ndarray | None = None
        self._sample_rate = 0
        self._state = PlayerState.IDLE
        self._stream: sd.OutputStream | None = None
        self._pos = 0
        self._lock = threading.Lock()
        self._has_more = False
        self._finished_pending = False   # báo "đã phát hết" đúng 1 lần cho UI

    @property
    def state(self) -> PlayerState:
        with self._lock:
            return self._state

    @property
    def is_playing(self) -> bool:
        with self._lock:
            return self._state is PlayerState.PLAYING

    @property
    def is_paused(self) -> bool:
        with self._lock:
            return self._state is PlayerState.PAUSED

    @property
    def is_buffering(self) -> bool:
        with self._lock:
            return self._state is PlayerState.BUFFERING

    @property
    def duration(self) -> float:
        with self._lock:
            if self._waveform is None or self._sample_rate <= 0:
                return 0.0
            return len(self._waveform) / self._sample_rate

    @property
    def has_more(self) -> bool:
        with self._lock:
            return self._has_more

    def set_has_more(self, has_more: bool) -> None:
        with self._lock:
            self._has_more = has_more

    def load(self, waveform: np.ndarray, sample_rate: int, has_more: bool = False) -> None:
        self._close_stream()
        with self._lock:
            self._waveform = np.asarray(waveform, dtype=np.float32)
            self._sample_rate = int(sample_rate)
            self._pos = 0
            self._state = PlayerState.IDLE
            self._has_more = has_more
            self._finished_pending = False
        self._open_stream()

    def append_audio(self, chunk: np.ndarray) -> None:
        """Nối thêm âm thanh động vào cuối waveform."""
        if len(chunk) == 0:
            return
        chunk = np.asarray(chunk, dtype=np.float32)
        should_resume_stream = False
        with self._lock:
            if self._waveform is None:
                self._waveform = chunk.copy()
            else:
                self._waveform = np.concatenate([self._waveform, chunk])

            # Nếu đang bị nghẽn do chờ âm thanh (BUFFERING) thì tự động kích hoạt phát tiếp
            if self._state is PlayerState.BUFFERING:
                self._state = PlayerState.PLAYING
                should_resume_stream = True

        if should_resume_stream:
            self._start_stream()

    def play(self, start_sec: float | None = None) -> None:
        close_needed = False
        with self._lock:
            if self._waveform is None or len(self._waveform) == 0:
                return
            if start_sec is not None:
                self._pos = int(np.clip(start_sec * self._sample_rate, 0, len(self._waveform)))
            elif self._state is PlayerState.STOPPED and self._pos >= len(self._waveform):
                self._pos = 0
            if self._state is PlayerState.STOPPED:
                # Stream có thể đã complete (hết file) -> bắt buộc mở lại mới
                close_needed = True
            self._finished_pending = False
        if close_needed:
            self._close_stream()
        self._start_stream()

    def pause(self) -> None:
        with self._lock:
            if self._state not in (PlayerState.PLAYING, PlayerState.BUFFERING):
                return
            self._state = PlayerState.PAUSED
        if self._stream is not None and self._stream.active:
            try:
                self._stream.stop()
            except Exception:
                pass

    def resume(self) -> None:
        with self._lock:
            if self._state is not PlayerState.PAUSED:
                return
        self._start_stream()

    def toggle(self) -> None:
        st = self.state
        if st in (PlayerState.PLAYING, PlayerState.BUFFERING):
            self.pause()
        elif st is PlayerState.PAUSED:
            self.resume()
        else:
            self.play()

    def stop(self) -> None:
        if self._stream is not None and self._stream.active:
            try:
                self._stream.stop()
            except Exception:
                pass
        with self._lock:
            self._pos = 0
            self._state = PlayerState.STOPPED
            self._has_more = False
            self._finished_pending = False

    def seek(self, seconds: float) -> None:
        with self._lock:
            if self._waveform is None or len(self._waveform) == 0:
                return
            target = float(np.clip(seconds, 0.0, max((len(self._waveform) - 1) / self._sample_rate, 0.0)))
            self._pos = int(target * self._sample_rate)
            self._finished_pending = False
            cur_state = self._state

        if cur_state is PlayerState.PLAYING and not (
            self._stream is not None and self._stream.active
        ):
            self._start_stream()

    def get_position(self) -> float:
        with self._lock:
            if self._waveform is None or self._sample_rate <= 0:
                return 0.0
            return min(self._pos / self._sample_rate, len(self._waveform) / self._sample_rate)

    def update(self) -> bool:
        """Gọi định kỳ (~40ms) từ UI: phát hiện audio đã phát hết — trả True đúng 1 lần."""
        with self._lock:
            # Callback đã báo hết file (paComplete) mà UI chưa kịp thấy
            if self._finished_pending and self._state is PlayerState.STOPPED:
                self._finished_pending = False
                return True
            if self._state not in (PlayerState.PLAYING, PlayerState.BUFFERING):
                return False
            # Nếu phát hết và không còn câu nào đang tạo ngầm -> kết thúc hẳn
            if self._waveform is not None and self._pos >= len(self._waveform):
                if not self._has_more:
                    self._state = PlayerState.STOPPED
                    self._finished_pending = False
                    if self._stream is not None and self._stream.active:
                        try:
                            self._stream.stop()
                        except Exception:
                            pass
                    return True
                else:
                    # Hết âm thanh nhưng đang tạo thêm -> chuyển sang BUFFERING
                    self._state = PlayerState.BUFFERING
            return False

    def _callback(self, outdata, frames, time_info, status) -> None:
        with self._lock:
            if self._waveform is None:
                outdata[:] = 0.0
                return

            available = len(self._waveform) - self._pos
            if available <= 0:
                outdata[:] = 0.0
                if self._has_more:
                    self._state = PlayerState.BUFFERING
                else:
                    self._state = PlayerState.STOPPED
                    self._finished_pending = True
                    raise sd.CallbackStop
                return

            n = min(available, frames)
            chunk = self._waveform[self._pos : self._pos + n]
            outdata[:n, 0] = chunk
            self._pos += n

            if n < frames:
                outdata[n:, 0] = 0.0
                if self._has_more:
                    self._state = PlayerState.BUFFERING
                else:
                    self._state = PlayerState.STOPPED
                    self._finished_pending = True
                    raise sd.CallbackStop

    def _open_stream(self) -> None:
        if self._stream is not None:
            return
        sr = self._sample_rate or 22050
        self._stream = sd.OutputStream(
            samplerate=sr,
            channels=1,
            dtype="float32",
            blocksize=0,
            callback=self._callback,
        )

    def _start_stream(self) -> None:
        self._open_stream()
        if self._stream is None:
            return
        with self._lock:
            self._state = PlayerState.PLAYING
        if not self._stream.active:
            try:
                self._stream.start()
            except Exception:
                pass
        if not self._stream.active:
            # Stream đã complete (hết file) hoặc lỗi -> mở stream mới
            self._close_stream()
            self._open_stream()
            if self._stream is not None:
                try:
                    self._stream.start()
                except Exception:
                    pass

    def _close_stream(self) -> None:
        if self._stream is not None:
            try:
                if self._stream.active:
                    self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    def quit(self) -> None:
        self._close_stream()
        with self._lock:
            self._state = PlayerState.STOPPED
            self._pos = 0
            self._has_more = False
