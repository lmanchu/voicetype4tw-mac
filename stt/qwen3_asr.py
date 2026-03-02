from .base import BaseSTT
import mlx_qwen3_asr
import numpy as np


class Qwen3ASRSTT(BaseSTT):
    def __init__(self):
        self._model = mlx_qwen3_asr.load_model("mlx-community/Qwen3-ASR-1.7B-4bit")

    def transcribe(self, audio_bytes: bytes, language: str = "zh") -> str:
        audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        return mlx_qwen3_asr.transcribe(audio_np, model=self._model, language=None)
