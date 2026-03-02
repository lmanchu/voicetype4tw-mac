import threading
import collections
import numpy as np
import sounddevice as sd
import io
import wave
from typing import Callable, Optional

PRE_BUFFER_SECS = 0.35  # seconds of audio to prepend on start (covers mic open latency)


class AudioRecorder:
    """
    Records audio from the default microphone.
    Keeps a continuous pre-buffer so speech at the very start of a PTT press
    is not lost due to microphone hardware warm-up latency.
    Provides real-time RMS level via callback for UI visualization.
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

        self._recording = False
        self._frames: list[np.ndarray] = []
        self._lock = threading.Lock()

        # Pre-buffer: ring buffer of recent audio chunks (always running)
        chunk_frames = int(samplerate * 0.05)
        pre_buf_chunks = int(PRE_BUFFER_SECS / 0.05) + 1
        self._pre_buf: collections.deque = collections.deque(maxlen=pre_buf_chunks)
        self._pre_buf_lock = threading.Lock()

        # Single persistent stream
        self._stream: Optional[sd.InputStream] = None
        self._poll_thread: Optional[threading.Thread] = None
        self._active = False
        self._open_stream()

    def _open_stream(self) -> None:
        """Open the persistent microphone stream and start polling."""
        self._active = True
        self._stream = sd.InputStream(
            samplerate=self.samplerate,
            channels=self.channels,
            dtype="int16",
        )
        self._stream.start()
        self._poll_thread = threading.Thread(target=self._poll_audio, daemon=True)
        self._poll_thread.start()

    def start(self) -> None:
        """Begin a recording session, prepending pre-buffered audio."""
        with self._lock:
            if self._recording:
                return
            # Snapshot current pre-buffer as the start of this recording
            with self._pre_buf_lock:
                self._frames = list(self._pre_buf)
            self._recording = True

    def _poll_audio(self) -> None:
        chunk_frames = int(self.samplerate * 0.05)
        while self._active and self._stream:
            try:
                if not self._stream.active:
                    break
                indata, _ = self._stream.read(chunk_frames)
                chunk = indata.copy()

                with self._lock:
                    if self._recording:
                        self._frames.append(chunk)
                    else:
                        with self._pre_buf_lock:
                            self._pre_buf.append(chunk)

                if self.level_callback:
                    rms = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2))) / 32768.0
                    self.level_callback(min(rms * 10, 1.0))

            except Exception:
                break

    def stop(self) -> bytes:
        """End the recording session and return WAV bytes."""
        with self._lock:
            self._recording = False
            frames = list(self._frames)
            self._frames = []

        return self._to_wav_bytes(frames)

    def close(self) -> None:
        """Shut down the persistent stream (call on app exit)."""
        self._active = False
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
            wf.setsampwidth(2)  # int16 = 2 bytes
            wf.setframerate(self.samplerate)
            wf.writeframes(audio.tobytes())
        return buf.getvalue()
