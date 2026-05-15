from __future__ import annotations

import logging
import time

import httpx

from app.core.config import settings
from app.providers.tts.base import TTSProvider
from app.providers.tts.schemas import TTSResult

logger = logging.getLogger(__name__)


class YandexSpeechKitTTSProvider(TTSProvider):
    provider_name = "yandex-speechkit"

    def synthesize(self, text: str, voice_settings: dict | None = None) -> TTSResult:
        if not settings.yandex_speechkit_api_key:
            raise ValueError("YANDEX_SPEECHKIT_API_KEY is not configured")
        if not settings.yandex_speechkit_folder_id:
            raise ValueError("YANDEX_SPEECHKIT_FOLDER_ID is not configured")
        voice = (voice_settings or {}).get("voice") or settings.yandex_speechkit_voice
        started_at = time.perf_counter()
        data = {
            "text": text,
            "lang": "ru-RU",
            "voice": voice,
            "folderId": settings.yandex_speechkit_folder_id,
            "format": "mp3",
        }
        with httpx.Client(timeout=settings.tts_timeout_seconds) as client:
            response = client.post(
                "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize",
                headers={"Authorization": f"Api-Key {settings.yandex_speechkit_api_key}"},
                data=data,
            )
            response.raise_for_status()
            audio_bytes = response.content
        duration_ms = round((time.perf_counter() - started_at) * 1000)
        logger.info("TTS provider completed", extra={"provider": self.provider_name, "duration_ms": duration_ms})
        return TTSResult(
            audio_bytes=audio_bytes,
            mime_type="audio/mpeg",
            duration_sec=None,
            provider=self.provider_name,
            voice_id=voice,
            raw_response={"provider": self.provider_name, "voice": voice, "duration_ms": duration_ms},
        )
