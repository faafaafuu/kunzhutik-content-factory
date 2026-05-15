from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.models.content_draft import ContentDraft
from app.models.media_asset import MediaAsset
from app.models.publication_task import PublicationTask
from app.providers.publishing.base import PublisherProvider
from app.providers.publishing.schemas import PublishResult


class MockPublisherProvider(PublisherProvider):
    provider_name = "mock-publication-v1"

    def publish(
        self,
        task: PublicationTask,
        assets: list[MediaAsset],
        draft: ContentDraft,
        context: dict | None = None,
    ) -> PublishResult:
        remote_id = f"mock-{task.platform.value}-{uuid4().hex[:12]}"
        return PublishResult(
            status="published",
            remote_id=remote_id,
            remote_url=f"https://example.local/{task.platform.value}/posts/{remote_id}",
            raw_response={
                "provider": self.provider_name,
                "platform": task.platform.value,
                "draft_id": str(draft.id),
                "asset_count": len(assets),
                "idempotency_key": task.idempotency_key,
                "published_at": datetime.now(timezone.utc).isoformat(),
            },
        )
