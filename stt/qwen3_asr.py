from .base import BaseSTT
import mlx_qwen3_asr
import numpy as np
import zhconv


class Qwen3ASRSTT(BaseSTT):
    def __init__(self):
        # load_model returns (model, config) tuple, so unpack it
        self._model, self._config = mlx_qwen3_asr.load_model("Qwen/Qwen3-ASR-0.6B")

    def transcribe(self, audio_bytes: bytes, language: str = "zh") -> str:
        audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        if len(audio_np) < 1600:  # less than 0.1s at 16kHz — skip
            return ""
        result = mlx_qwen3_asr.transcribe(audio_np, model=self._model, language="zh")
        text = result.text.strip() if result and result.text else ""
        # Force Traditional Chinese output
        return zhconv.convert(text, "zh-tw") if text else ""
