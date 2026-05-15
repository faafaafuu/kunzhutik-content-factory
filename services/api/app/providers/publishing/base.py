from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.content_draft import ContentDraft
from app.models.media_asset import MediaAsset
from app.models.publication_task import PublicationTask
from app.providers.publishing.schemas import PublishResult


class PublisherProvider(ABC):
    provider_name: str

    @abstractmethod
    def publish(
        self,
        task: PublicationTask,
        assets: list[MediaAsset],
        draft: ContentDraft,
        context: dict | None = None,
    ) -> PublishResult:
        raise NotImplementedError
