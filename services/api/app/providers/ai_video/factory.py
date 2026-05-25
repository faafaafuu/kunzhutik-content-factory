from __future__ import annotations

import logging

from app.core.config import settings
from app.providers.ai_video.base import AIVideoProvider
from app.providers.ai_video.kling import KlingAIVideoProvider
from app.providers.ai_video.mock import MockAIVideoProvider
from app.providers.ai_video.runway import RunwayAIVideoProvider

logger = logging.getLogger(__name__)


def get_ai_video_provider() -> AIVideoProvider:
    provider = settings.ai_video_provider.lower().strip()
    if provider in {"mock", "fallback"}:
        return MockAIVideoProvider()
    if provider == "kling":
        return KlingAIVideoProvider()
    if provider == "runway":
        return RunwayAIVideoProvider()
    raise ValueError(f"Unsupported AI_VIDEO_PROVIDER: {settings.ai_video_provider}")
