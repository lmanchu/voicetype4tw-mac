import threading
import collections
import numpy as np
import sounddevice as sd
import io
import wave
from typing import Callable, Optional

PRE_BUFFER_SECS = 0.35  # seconds to prepend on PTT press


class AudioRecorder:
    """
    Records audio from the default microphone.

    A single persistent stream runs from app start.  The poll thread writes
    into a ring buffer (pre-buffer mode) or into _frames (recording mode),
    toggled atomically by a flag.  This eliminates the mic warm-up gap.
    """

    def __init__(
        self,
        samplerate: int = 16000,
        channels: int = 1,
        level_callback: Optional[Callable[[float], None]] = None,
    ):
        self.samplerate = samplerate
        self.channels = channels
        self.level_callback = level_callback

        chunk_frames = int(samplerate * 0.05)
        self._chunk_frames = chunk_frames
        pre_buf_chunks = int(PRE_BUFFER_SECS / 0.05) + 2

        self._pre_buf: collections.deque = collections.deque(maxlen=pre_buf_chunks)
        self._frames: list[np.ndarray] = []
        self._recording = False   # toggled under _lock
        self._lock = threading.Lock()

        self._stream: Optional[sd.InputStream] = None
        self._stream_ok = False
        self._poll_thread: Optional[threading.Thread] = None
        self._alive = True

        self._open_persistent_stream()

    def _open_persistent_stream(self) -> None:
        try:
            self._stream = sd.InputStream(
                samplerate=self.samplerate,
                channels=self.channels,
                dtype="int16",
            )
            self._stream.start()
            self._stream_ok = True
            self._poll_thread = threading.Thread(target=self._poll, daemon=True)
            self._poll_thread.start()
        except Exception as e:
            print(f"[recorder] persistent stream failed ({e}), using fallback mode")
            self._stream = None
            self._stream_ok = False

    def _poll(self) -> None:
        """Single poll loop — writes to pre_buf or _frames based on _recording flag."""
        while self._alive:
            try:
                if not self._stream or not self._stream.active:
                    break
                indata, _ = self._stream.read(self._chunk_frames)
                chunk = indata.copy()

                with self._lock:
                    if self._recording:
                        self._frames.append(chunk)
                    else:
                        self._pre_buf.append(chunk)

                if self.level_callback and self._recording:
                    rms = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2))) / 32768.0
                    self.level_callback(min(rms * 10, 1.0))

            except Exception:
                break
        self._stream_ok = False

    def start(self) -> None:
        """Begin a recording session."""
        if self._stream_ok:
            # Persistent stream: snapshot pre-buffer and flip to recording mode
            with self._lock:
                if self._recording:
                    return
                self._frames = list(self._pre_buf)
                self._recording = True
        else:
            # Fallback: open a fresh stream (no pre-buffer)
            with self._lock:
                if self._recording:
                    return
                self._frames = []
                self._recording = True
            try:
                self._stream = sd.InputStream(
                    samplerate=self.samplerate,
                    channels=self.channels,
                    dtype="int16",
                )
                self._stream.start()
                self._stream_ok = True
                self._alive = True
                self._poll_thread = threading.Thread(target=self._poll, daemon=True)
                self._poll_thread.start()
            except Exception as e:
                print(f"[recorder] fallback stream failed: {e}")
                with self._lock:
                    self._recording = False

    def stop(self) -> bytes:
        """End the recording session and return WAV bytes."""
        with self._lock:
            self._recording = False
            frames = list(self._frames)
            self._frames = []
            self._pre_buf.clear()   # fresh pre-buffer for next session

        return self._to_wav_bytes(frames)

    def close(self) -> None:
        """Shut down all streams on app exit."""
        self._alive = False
        self._recording = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    def _to_wav_bytes(self, frames: list) -> bytes:
        if not frames:
            return b""
        audio = np.concatenate(frames, axis=0)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)
            wf.setframerate(self.samplerate)
            wf.writeframes(audio.tobytes())
        return buf.getvalue()
