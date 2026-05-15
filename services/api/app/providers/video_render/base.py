from __future__ import annotations

from abc import ABC, abstractmethod

from app.providers.video_render.schemas import RenderContent, VideoRenderResult


class VideoRenderProvider(ABC):
    provider_name: str

    @abstractmethod
    def render(
        self,
        source_image_url: str | None,
        voice_asset_url: str | None,
        content: RenderContent,
        format: str,
        template_key: str,
        context: dict | None = None,
    ) -> VideoRenderResult:
        raise NotImplementedError
