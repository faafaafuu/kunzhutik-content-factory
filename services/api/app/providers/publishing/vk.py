from __future__ import annotations

import logging
import time

import httpx

from app.core.config import settings
from app.models.content_draft import ContentDraft
from app.models.media_asset import MediaAsset
from app.models.publication_task import PublicationTask
from app.providers.publishing.base import PublisherProvider
from app.providers.publishing.schemas import PublishResult

logger = logging.getLogger(__name__)


class VKPublisherProvider(PublisherProvider):
    provider_name = "vk-wall-post-v1"

    def publish(
        self,
        task: PublicationTask,
        assets: list[MediaAsset],
        draft: ContentDraft,
        context: dict | None = None,
    ) -> PublishResult:
        if not settings.vk_access_token or not settings.vk_group_id:
            raise ValueError("VK publisher requires VK_ACCESS_TOKEN and VK_GROUP_ID")

        started_at = time.perf_counter()
        payload = {
            "access_token": settings.vk_access_token,
            "v": settings.vk_api_version,
            "owner_id": f"-{settings.vk_group_id}",
            "from_group": 1,
            "message": _message_from_draft(draft),
            "guid": task.idempotency_key,
        }
        with httpx.Client(timeout=settings.publisher_timeout_seconds) as client:
            response = client.post("https://api.vk.com/method/wall.post", data=payload)
            response.raise_for_status()
            body = response.json()

        duration_ms = round((time.perf_counter() - started_at) * 1000)
        logger.info("VK publication completed", extra={"duration_ms": duration_ms, "publication_task_id": str(task.id)})
        if "error" in body:
            error = body["error"]
            raise ValueError(f"VK API error {error.get('error_code')}: {error.get('error_msg')}")

        post_id = body.get("response", {}).get("post_id")
        remote_id = str(post_id) if post_id is not None else None
        remote_url = f"https://vk.com/wall-{settings.vk_group_id}_{post_id}" if post_id is not None else None
        return PublishResult(
            status="published",
            remote_id=remote_id,
            remote_url=remote_url,
            raw_response={
                "provider": self.provider_name,
                "platform": task.platform.value,
                "asset_count": len(assets),
                "duration_ms": duration_ms,
                "vk_response": body,
                "media_upload": "not_implemented_text_only_wall_post",
            },
        )


def _message_from_draft(draft: ContentDraft) -> str:
    parts = [draft.caption.strip()]
    if draft.cta:
        parts.append(draft.cta.strip())
    hashtags = (draft.metadata_json or {}).get("hashtags", [])
    if hashtags:
        parts.append(" ".join(hashtags))
    return "\n\n".join(part for part in parts if part)
