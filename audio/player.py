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


class ArraySource:
    """Source âm thanh nằm trong RAM (mảng float32 mono)."""

    def __init__(self, waveform: np.ndarray | None = None) -> None:
        self._data = np.asarray(
            waveform if waveform is not None else np.zeros(0), dtype=np.float32
        ).reshape(-1)

    @property
    def total_samples(self) -> int:
        return int(self._data.size)

    def read(self, start: int, n: int) -> np.ndarray:
        start = max(0, int(start))
        if start >= self._data.size:
            return np.zeros(0, dtype=np.float32)
        end = min(self._data.size, start + max(0, int(n)))
        return self._data[start:end]


class AudioPlayer:
    """Phát âm thanh bằng stream liên tục (sounddevice).

    - Nguồn âm thanh là "source" bất kỳ có .total_samples + .read(start, n)
      (ArraySource / GrowableBuffer / TempAudioStore) -> không copy dữ liệu.
    - Source có thể lớn dần (streaming): player tự đọc phần mới xuất hiện.
    - Tự động chuyển BUFFERING khi đệm trống mà chưa xong (has_more=True).
    - Tự động phát tiếp ngay khi có audio mới nạp vào.
    """

    def __init__(self) -> None:
        self._source: ArraySource | None = None
        self._sample_rate = 0
        self._state = PlayerState.IDLE
        self._stream: sd.OutputStream | None = None
        self._pos = 0
        self._lock = threading.Lock()
        self._has_more = False
        self._finished_pending = False   # báo "đã phát hết" đúng 1 lần cho UI
        self._available = True           # False nếu không mở được thiết bị âm thanh
        self._device_error = ""

    @property
    def available(self) -> bool:
        """False nếu không mở được thiết bị phát (VD máy không có sound card)."""
        return self._available

    @property
    def device_error(self) -> str:
        return self._device_error

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
            total = self._total_samples()
            return total / self._sample_rate if self._sample_rate > 0 else 0.0

    @property
    def has_more(self) -> bool:
        with self._lock:
            return self._has_more

    def set_has_more(self, has_more: bool) -> None:
        with self._lock:
            self._has_more = has_more

    # ── helpers ──

    def _total_samples(self) -> int:
        if self._source is None:
            return 0
        return int(getattr(self._source, "total_samples", 0) or 0)

    # ── Nạp nguồn ──

    def load_source(self, source, sample_rate: int, has_more: bool = False) -> None:
        """Nạp một source âm thanh (RAM hoặc đĩa)."""
        self._close_stream()
        with self._lock:
            self._source = source
            self._sample_rate = int(sample_rate)
            self._pos = 0
            self._state = PlayerState.IDLE
            self._has_more = has_more
            self._finished_pending = False
        self._open_stream()

    def load(self, waveform: np.ndarray, sample_rate: int, has_more: bool = False) -> None:
        """Nạp mảng âm thanh trong RAM (dùng cho test nhanh)."""
        self.load_source(ArraySource(waveform), sample_rate, has_more)

    def append_audio(self, chunk: np.ndarray) -> None:
        """Nối thêm âm thanh động (chỉ hỗ trợ nguồn kiểu buffer trong RAM)."""
        if chunk is None or len(chunk) == 0:
            return
        source = self._source
        append = getattr(source, "append", None)
        if append is None:
            return
        should_resume_stream = False
        with self._lock:
            append(np.asarray(chunk, dtype=np.float32))
            # Nếu đang bị nghẽn do chờ âm thanh (BUFFERING) thì tự động kích hoạt phát tiếp
            if self._state is PlayerState.BUFFERING:
                self._state = PlayerState.PLAYING
                should_resume_stream = True
        if should_resume_stream:
            self._start_stream()

    # ── Điều khiển ──

    def play(self, start_sec: float | None = None) -> None:
        close_needed = False
        with self._lock:
            if self._source is None or self._total_samples() == 0:
                return
            if start_sec is not None:
                self._pos = int(
                    np.clip(start_sec * self._sample_rate, 0, self._total_samples())
                )
            elif self._state is PlayerState.STOPPED and self._pos >= self._total_samples():
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
            total = self._total_samples()
            if total == 0:
                return
            target = float(
                np.clip(seconds, 0.0, max((total - 1) / self._sample_rate, 0.0))
            )
            self._pos = int(target * self._sample_rate)
            self._finished_pending = False
            cur_state = self._state

        if cur_state is PlayerState.PLAYING and not (
            self._stream is not None and self._stream.active
        ):
            self._start_stream()

    def get_position(self) -> float:
        with self._lock:
            total = self._total_samples()
            if total == 0 or self._sample_rate <= 0:
                return 0.0
            return min(self._pos / self._sample_rate, total / self._sample_rate)

    def update(self) -> bool:
        """Gọi định kỳ (~40ms) từ UI: phát hiện audio đã phát hết — trả True đúng 1 lần."""
        need_restart = False
        with self._lock:
            # Callback đã báo hết file (paComplete) mà UI chưa kịp thấy
            if self._finished_pending and self._state is PlayerState.STOPPED:
                self._finished_pending = False
                return True
            if self._state not in (PlayerState.PLAYING, PlayerState.BUFFERING):
                return False
            total = self._total_samples()
            if self._state is PlayerState.BUFFERING and self._pos < total:
                # Source vừa lớn lên (stream/cập nhật) -> có dữ liệu mới, chơi tiếp
                self._state = PlayerState.PLAYING
                need_restart = (self._stream is None or not self._stream.active)
            elif self._pos >= total:
                # Nếu phát hết và không còn câu nào đang tạo ngầm -> kết thúc hẳn
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
        if need_restart:
            self._start_stream()
        return False

    def _callback(self, outdata, frames, time_info, status) -> None:
        with self._lock:
            source = self._source
            if source is None:
                outdata[:] = 0.0
                return

            total = self._total_samples()
            available = total - self._pos
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
            chunk = source.read(self._pos, n)
            if chunk is None or chunk.size == 0:
                chunk = np.zeros(0, dtype=np.float32)
            outdata[: len(chunk), 0] = chunk
            if len(chunk) < outdata.shape[0]:
                outdata[len(chunk):, 0] = 0.0
            self._pos += len(chunk)

            if len(chunk) < frames:
                if self._has_more:
                    self._state = PlayerState.BUFFERING
                else:
                    self._state = PlayerState.STOPPED
                    self._finished_pending = True
                    raise sd.CallbackStop

    def _open_stream(self) -> None:
        if self._stream is not None or not self._available:
            return
        sr = self._sample_rate or 22050
        try:
            self._stream = sd.OutputStream(
                samplerate=sr,
                channels=1,
                dtype="float32",
                blocksize=0,
                callback=self._callback,
            )
        except Exception as exc:
            # Không có thiết bị âm thanh (hoặc bị khoá) -> app vẫn xuất file được.
            self._available = False
            self._device_error = str(exc)
            self._stream = None

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
