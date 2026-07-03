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
from app.services.storage import download_bytes
from shared.enums import AssetKind

logger = logging.getLogger(__name__)

VK_API_BASE = "https://api.vk.com/method"


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
        attachment = None
        video_upload_info: dict = {"media_upload": "no_video_asset_found"}
        video_asset = _select_final_video(assets)
        with httpx.Client(timeout=max(settings.publisher_timeout_seconds, 120)) as client:
            if video_asset is not None:
                try:
                    attachment, video_upload_info = _upload_video(client, video_asset, draft)
                except Exception as exc:
                    # Video upload requires a user token with the "video" scope; a plain
                    # community token cannot call video.save. Degrade to a text post so
                    # the publication is not lost, and surface the reason in the payload.
                    logger.warning("VK video upload failed, falling back to text post: %s", exc)
                    video_upload_info = {"media_upload": "failed_fallback_to_text", "error": str(exc)}

            payload = {
                "access_token": settings.vk_access_token,
                "v": settings.vk_api_version,
                "owner_id": f"-{settings.vk_group_id}",
                "from_group": 1,
                "message": _message_from_draft(draft),
                "guid": task.idempotency_key,
            }
            if attachment:
                payload["attachments"] = attachment
            response = client.post(f"{VK_API_BASE}/wall.post", data=payload)
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
                **video_upload_info,
            },
        )


def _select_final_video(assets: list[MediaAsset]) -> MediaAsset | None:
    videos = [asset for asset in assets if asset.kind == AssetKind.video]
    if not videos:
        return None
    for asset in videos:
        if (asset.metadata_json or {}).get("provider") == "ai-video-final-render":
            return asset
    return max(videos, key=lambda asset: asset.created_at)


def _upload_video(client: httpx.Client, asset: MediaAsset, draft: ContentDraft) -> tuple[str, dict]:
    save_payload = {
        "access_token": settings.vk_access_token,
        "v": settings.vk_api_version,
        "group_id": settings.vk_group_id,
        "name": (draft.title or draft.caption or "Кунжутик")[:100],
        "description": (draft.caption or "")[:500],
        "wallpost": 0,
    }
    save_response = client.post(f"{VK_API_BASE}/video.save", data=save_payload)
    save_response.raise_for_status()
    save_body = save_response.json()
    if "error" in save_body:
        error = save_body["error"]
        raise ValueError(f"VK video.save error {error.get('error_code')}: {error.get('error_msg')}")

    save_data = save_body["response"]
    upload_url = save_data["upload_url"]
    video_bytes = download_bytes(asset.storage_key)
    upload_response = client.post(upload_url, files={"video_file": (asset.file_name, video_bytes, asset.mime_type)})
    upload_response.raise_for_status()
    upload_body = upload_response.json()
    if upload_body.get("error"):
        raise ValueError(f"VK video upload error: {upload_body['error']}")

    owner_id = save_data.get("owner_id")
    video_id = upload_body.get("video_id") or save_data.get("video_id")
    if owner_id is None or video_id is None:
        raise ValueError(f"VK video upload returned no video id: save={save_data}, upload={upload_body}")
    attachment = f"video{owner_id}_{video_id}"
    return attachment, {
        "media_upload": "video_attached",
        "vk_video_id": video_id,
        "vk_video_owner_id": owner_id,
        "video_size_bytes": len(video_bytes),
    }


def _message_from_draft(draft: ContentDraft) -> str:
    parts = [draft.caption.strip()]
    if draft.cta:
        parts.append(draft.cta.strip())
    hashtags = (draft.metadata_json or {}).get("hashtags", [])
    if hashtags:
        parts.append(" ".join(hashtags))
    return "\n\n".join(part for part in parts if part)
