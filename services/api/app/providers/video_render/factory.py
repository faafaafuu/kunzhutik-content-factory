from __future__ import annotations

import logging
import time

from app.core.config import settings
from app.providers.video_render.base import VideoRenderProvider
from app.providers.video_render.creatomate import CreatomateVideoRenderProvider
from app.providers.video_render.ffmpeg_fallback import FfmpegVideoRenderProvider
from app.providers.video_render.schemas import RenderContent, VideoRenderResult

logger = logging.getLogger(__name__)


class FallbackVideoRenderProvider(VideoRenderProvider):
    def __init__(self, primary: VideoRenderProvider, fallback: VideoRenderProvider) -> None:
        self.primary = primary
        self.fallback = fallback
        self.provider_name = primary.provider_name

    def render(
        self,
        source_image_url: str | None,
        voice_asset_url: str | None,
        content: RenderContent,
        format: str,
        template_key: str,
        context: dict | None = None,
    ) -> VideoRenderResult:
        started_at = time.perf_counter()
        try:
            result = self.primary.render(source_image_url, voice_asset_url, content, format, template_key, context)
            if result.video_bytes or result.video_url:
                return result
            raise ValueError(f"Video provider returned no video asset; status={result.status}")
        except Exception as exc:
            duration_ms = round((time.perf_counter() - started_at) * 1000)
            logger.exception(
                "Video render provider failed; falling back to ffmpeg",
                extra={"provider": self.primary.provider_name, "duration_ms": duration_ms, "error": str(exc)},
            )
            if not settings.enable_provider_fallback:
                raise
            result = self.fallback.render(source_image_url, voice_asset_url, content, format, template_key, context)
            result.raw_response["fallback_reason"] = str(exc)
            result.raw_response["requested_provider"] = self.primary.provider_name
            result.raw_response["provider"] = self.fallback.provider_name
            return result


def get_video_render_provider() -> VideoRenderProvider:
    provider = settings.video_provider.lower().strip()
    if provider == "creatomate":
        return FallbackVideoRenderProvider(CreatomateVideoRenderProvider(), FfmpegVideoRenderProvider())
    if provider in {"ffmpeg", "mock", "fallback"}:
        return FfmpegVideoRenderProvider()
    raise ValueError(f"Unsupported VIDEO_PROVIDER: {settings.video_provider}")
