from __future__ import annotations

import logging
import time

from app.core.config import settings
from app.models.content_draft import ContentDraft
from app.models.media_asset import MediaAsset
from app.models.publication_task import PublicationTask
from app.providers.publishing.base import PublisherProvider
from app.providers.publishing.instagram_manual import InstagramManualPublisherProvider
from app.providers.publishing.mock import MockPublisherProvider
from app.providers.publishing.vk import VKPublisherProvider
from app.providers.publishing.yandex_manual import YandexManualPublisherProvider
from shared.enums import ContentPlatform

logger = logging.getLogger(__name__)


class FallbackPublisherProvider(PublisherProvider):
    def __init__(self, primary: PublisherProvider, fallback: PublisherProvider) -> None:
        self.primary = primary
        self.fallback = fallback
        self.provider_name = primary.provider_name

    def publish(
        self,
        task: PublicationTask,
        assets: list[MediaAsset],
        draft: ContentDraft,
        context: dict | None = None,
    ) -> PublishResult:
        started_at = time.perf_counter()
        try:
            return self.primary.publish(task, assets, draft, context)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - started_at) * 1000)
            logger.exception(
                "Publisher provider failed; falling back to mock",
                extra={"provider": self.primary.provider_name, "duration_ms": duration_ms, "error": str(exc)},
            )
            if not settings.enable_provider_fallback:
                raise
            result = self.fallback.publish(task, assets, draft, context)
            result.raw_response["fallback_reason"] = str(exc)
            result.raw_response["requested_provider"] = self.primary.provider_name
            result.raw_response["provider"] = self.fallback.provider_name
            return result


def get_publisher_provider(platform: ContentPlatform | None = None) -> PublisherProvider:
    provider = settings.publisher_provider.lower().strip()
    if provider == "mock":
        return MockPublisherProvider()
    if provider == "vk":
        if platform == ContentPlatform.instagram:
            return InstagramManualPublisherProvider()
        if platform == ContentPlatform.yandex_maps:
            return YandexManualPublisherProvider()
        return FallbackPublisherProvider(VKPublisherProvider(), MockPublisherProvider())
    if provider in {"manual", "manual_package"}:
        return _manual_provider_for_platform(platform)
    if provider in {"instagram_manual", "instagram-manual"}:
        return InstagramManualPublisherProvider()
    if provider in {"yandex_manual", "yandex-manual"}:
        return YandexManualPublisherProvider()
    raise ValueError(f"Unsupported PUBLISHER_PROVIDER: {settings.publisher_provider}")


def _manual_provider_for_platform(platform: ContentPlatform | None) -> PublisherProvider:
    if platform == ContentPlatform.yandex_maps:
        return YandexManualPublisherProvider()
    if platform == ContentPlatform.instagram:
        return InstagramManualPublisherProvider()
    return MockPublisherProvider()
