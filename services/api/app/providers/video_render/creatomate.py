from __future__ import annotations

import httpx

from app.core.config import settings
from app.providers.video_render.base import VideoRenderProvider
from app.providers.video_render.schemas import RenderContent, VideoRenderResult


class CreatomateVideoRenderProvider(VideoRenderProvider):
    provider_name = "creatomate"

    def render(
        self,
        source_image_url: str | None,
        voice_asset_url: str | None,
        content: RenderContent,
        format: str,
        template_key: str,
        context: dict | None = None,
    ) -> VideoRenderResult:
        if not settings.creatomate_api_key:
            raise ValueError("CREATOMATE_API_KEY is not configured")
        template_id = settings.creatomate_template_9_16 if format == "9:16" else settings.creatomate_template_1_1
        if not template_id:
            raise ValueError(f"Creatomate template is not configured for format {format}")
        payload = {
            "template_id": template_id,
            "modifications": {
                "Title": content.title,
                "Subtitle": content.subtitle,
                "Image": source_image_url,
                "Audio": voice_asset_url,
            },
        }
        with httpx.Client(timeout=settings.video_render_timeout_seconds) as client:
            response = client.post(
                "https://api.creatomate.com/v1/renders",
                headers={"Authorization": f"Bearer {settings.creatomate_api_key}"},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        render = data[0] if isinstance(data, list) and data else data
        return VideoRenderResult(
            video_url=render.get("url"),
            preview_url=render.get("snapshot_url"),
            provider=self.provider_name,
            render_id=render.get("id"),
            status=render.get("status", "planned"),
            raw_response={"provider": self.provider_name, "response": data},
        )
