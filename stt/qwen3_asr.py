"""
Qwen3-ASR STT engine — cross-platform.
macOS: uses mlx_qwen3_asr (Apple Silicon MLX acceleration)
Windows: uses official qwen_asr package (PyTorch)
"""
from .base import BaseSTT
import platform
import zhconv

IS_WINDOWS = platform.system() == "Windows"


class Qwen3ASRSTT(BaseSTT):
    def __init__(self):
        if IS_WINDOWS:
            self._init_torch()
        else:
            self._init_mlx()

    def _init_mlx(self):
        import mlx_qwen3_asr
        self._backend = "mlx"
        self._model, self._config = mlx_qwen3_asr.load_model("Qwen/Qwen3-ASR-0.6B")

    def _init_torch(self):
        import torch
        from qwen_asr import Qwen3ASRModel

        self._backend = "torch"
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if device != "cpu" else torch.float32

        self._torch_model = Qwen3ASRModel.from_pretrained(
            "Qwen/Qwen3-ASR-0.6B",
            dtype=dtype,
            device_map=device,
            max_new_tokens=512,
        )
        print(f"[stt] Qwen3-ASR loaded on {device}.")

    def transcribe(self, audio_bytes: bytes, language: str = "zh") -> str:
        if not audio_bytes:
            return ""
        if self._backend == "mlx":
            return self._transcribe_mlx(audio_bytes, language)
        else:
            return self._transcribe_torch(audio_bytes, language)

    def _transcribe_mlx(self, audio_bytes: bytes, language: str) -> str:
        import numpy as np
        import mlx_qwen3_asr

        audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        if len(audio_np) < 1600:
            return ""
        result = mlx_qwen3_asr.transcribe(audio_np, model=self._model, language="zh")
        text = result.text.strip() if result and result.text else ""
        return zhconv.convert(text, "zh-tw") if text else ""

    def _transcribe_torch(self, audio_bytes: bytes, language: str) -> str:
        import tempfile
        import os

        LANG_MAP = {
            "zh": "Chinese", "en": "English", "ja": "Japanese",
            "ko": "Korean", "de": "German", "fr": "French", "es": "Spanish",
        }

        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        try:
            tmp.write(audio_bytes)
            tmp.close()

            results = self._torch_model.transcribe(
                audio=tmp.name,
                language=LANG_MAP.get(language, "Chinese"),
            )

            if not results or not results[0].text:
                return ""

            text = results[0].text.strip()
            text = zhconv.convert(text, "zh-tw") if text else ""
            print(f"[stt] Qwen3-ASR transcribed: {text}")
            return text
        finally:
            os.unlink(tmp.name)
