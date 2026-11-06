import threading

import numpy as np
import sounddevice as sd

import config


class Recorder:
    """Records microphone audio between start() and stop()."""

    def __init__(self, sample_rate: int = config.SAMPLE_RATE):
        self.sample_rate = sample_rate
        self._chunks: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()
        self.level = 0.0  # latest input loudness, 0..1

    def _callback(self, indata, frames, time, status):
        self._chunks.append(indata.copy())
        self.level = min(1.0, float(np.sqrt(np.mean(indata**2))) * 10)

    def start(self) -> None:
        with self._lock:
            if self._stream is not None:
                return
            self._chunks = []
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                callback=self._callback,
            )
            self._stream.start()

    def stop(self) -> np.ndarray:
        """Stop recording and return mono float32 audio."""
        with self._lock:
            if self._stream is None:
                return np.zeros(0, dtype="float32")
            self._stream.stop()
            self._stream.close()
            self._stream = None
            chunks, self._chunks = self._chunks, []
        if not chunks:
            return np.zeros(0, dtype="float32")
        return np.concatenate(chunks).flatten()
