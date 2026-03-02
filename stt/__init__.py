from .base import BaseSTT


def get_stt(config: dict) -> BaseSTT:
    engine = config.get("stt_engine", "local_whisper")

    if engine == "mlx_whisper":
        from .mlx_whisper import MLXWhisperSTT
        return MLXWhisperSTT(config)
    elif engine == "groq":
        from .groq_whisper import GroqWhisperSTT
        return GroqWhisperSTT(config)
    elif engine == "openrouter":
        from .openrouter_stt import OpenRouterSTT
        return OpenRouterSTT(config)
    elif engine == "gemini":
        from .gemini_stt import GeminiSTT
        return GeminiSTT(config)
    elif engine == "qwen3_asr":
        from .qwen3_asr import Qwen3ASRSTT
        return Qwen3ASRSTT()
    else:
        from .local_whisper import LocalWhisperSTT
        return LocalWhisperSTT(config)
