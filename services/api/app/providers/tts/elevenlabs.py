from __future__ import annotations

import logging
import time

import httpx

from app.core.config import settings
from app.providers.tts.base import TTSProvider
from app.providers.tts.schemas import TTSResult

logger = logging.getLogger(__name__)


class ElevenLabsTTSProvider(TTSProvider):
    provider_name = "elevenlabs"

    def synthesize(self, text: str, voice_settings: dict | None = None) -> TTSResult:
        if not settings.elevenlabs_api_key:
            raise ValueError("ELEVENLABS_API_KEY is not configured")
        voice_id = (voice_settings or {}).get("voice_id") or settings.elevenlabs_voice_id
        if not voice_id:
            raise ValueError("ELEVENLABS_VOICE_ID is not configured")
        model_id = (voice_settings or {}).get("model_id") or settings.elevenlabs_model_id
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        started_at = time.perf_counter()
        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": float((voice_settings or {}).get("stability", 0.45)),
                "similarity_boost": float((voice_settings or {}).get("similarity_boost", 0.75)),
            },
        }
        with httpx.Client(timeout=settings.tts_timeout_seconds) as client:
            response = client.post(
                url,
                headers={"xi-api-key": settings.elevenlabs_api_key, "Accept": "audio/mpeg"},
                json=payload,
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
            voice_id=voice_id,
            raw_response={"provider": self.provider_name, "model_id": model_id, "duration_ms": duration_ms},
        )
