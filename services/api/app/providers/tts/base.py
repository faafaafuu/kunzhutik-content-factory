from __future__ import annotations

from abc import ABC, abstractmethod

from app.providers.tts.schemas import TTSResult


class TTSProvider(ABC):
    provider_name: str

    @abstractmethod
    def synthesize(self, text: str, voice_settings: dict | None = None) -> TTSResult:
        raise NotImplementedError
