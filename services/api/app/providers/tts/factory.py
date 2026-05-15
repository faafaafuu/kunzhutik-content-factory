from __future__ import annotations

import logging
import time

from app.core.config import settings
from app.providers.tts.base import TTSProvider
from app.providers.tts.elevenlabs import ElevenLabsTTSProvider
from app.providers.tts.mock import EspeakTTSProvider
from app.providers.tts.schemas import TTSResult
from app.providers.tts.yandex_speechkit import YandexSpeechKitTTSProvider

logger = logging.getLogger(__name__)


class FallbackTTSProvider(TTSProvider):
    def __init__(self, primary: TTSProvider, fallback: TTSProvider) -> None:
        self.primary = primary
        self.fallback = fallback
        self.provider_name = primary.provider_name

    def synthesize(self, text: str, voice_settings: dict | None = None) -> TTSResult:
        started_at = time.perf_counter()
        try:
            return self.primary.synthesize(text, voice_settings)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - started_at) * 1000)
            logger.exception(
                "TTS provider failed; falling back to espeak",
                extra={"provider": self.primary.provider_name, "duration_ms": duration_ms, "error": str(exc)},
            )
            if not settings.enable_provider_fallback:
                raise
            result = self.fallback.synthesize(text, voice_settings)
            result.raw_response["fallback_reason"] = str(exc)
            result.raw_response["requested_provider"] = self.primary.provider_name
            result.raw_response["provider"] = self.fallback.provider_name
            return result


def get_tts_provider() -> TTSProvider:
    provider = settings.tts_provider.lower().strip()
    if provider == "elevenlabs":
        return FallbackTTSProvider(ElevenLabsTTSProvider(), EspeakTTSProvider())
    if provider in {"yandex_speechkit", "yandex-speechkit", "yandex"}:
        return FallbackTTSProvider(YandexSpeechKitTTSProvider(), EspeakTTSProvider())
    if provider in {"mock", "espeak", "espeak-ng", "fallback"}:
        return EspeakTTSProvider()
    raise ValueError(f"Unsupported TTS_PROVIDER: {settings.tts_provider}")
