from __future__ import annotations

from app.models.content_draft import ContentDraft
from app.models.media_asset import MediaAsset
from app.models.publication_task import PublicationTask
from app.providers.publishing.base import PublisherProvider
from app.providers.publishing.manual_package import build_manual_package
from app.providers.publishing.schemas import PublishResult


class InstagramManualPublisherProvider(PublisherProvider):
    provider_name = "instagram-manual-package-v1"

    def publish(
        self,
        task: PublicationTask,
        assets: list[MediaAsset],
        draft: ContentDraft,
        context: dict | None = None,
    ) -> PublishResult:
        package = build_manual_package(task, assets, draft, platform_label="Instagram")
        return PublishResult(
            status="published",
            remote_id=package["package_id"],
            remote_url=package["package_url"],
            raw_response={"provider": self.provider_name, **package},
        )
