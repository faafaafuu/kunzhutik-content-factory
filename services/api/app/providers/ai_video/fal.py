from __future__ import annotations

import hashlib
import logging
import time

import httpx

from app.core.config import settings
from app.providers.ai_video.base import AIVideoProvider
from app.providers.ai_video.schemas import AIVideoSceneResult

logger = logging.getLogger(__name__)

FAL_QUEUE_BASE_URL = "https://queue.fal.run"
FAL_STORAGE_INITIATE_URL = "https://rest.alpha.fal.ai/storage/upload/initiate?storage_type=fal-cdn-v3"

TERMINAL_STATUSES = {"COMPLETED"}
FAILED_STATUSES = {"FAILED", "CANCELLED", "ERROR"}


class FalAIVideoProvider(AIVideoProvider):
    """AI-video scenes through fal.ai queue API.

    One AI_VIDEO_FAL_KEY covers every fal-hosted model (Seedance, PixVerse, Kling, Hailuo);
    the model is switched with AI_VIDEO_FAL_MODEL without code changes.
    """

    provider_name = "fal"

    def __init__(self) -> None:
        # Same dish photo is reused by every scene in a plan; upload it to fal storage once.
        self._upload_cache: dict[str, str] = {}

    def generate_scene(
        self,
        prompt: str,
        image_reference_url: str | None,
        character_reference_url: str | None,
        duration_sec: float,
        aspect_ratio: str,
        context: dict | None = None,
    ) -> AIVideoSceneResult:
        if not settings.ai_video_fal_key:
            raise ValueError("AI_VIDEO_FAL_KEY is not configured")
        if not settings.ai_video_fal_model:
            raise ValueError("AI_VIDEO_FAL_MODEL is not configured")

        ctx = context or {}
        started_at = time.perf_counter()
        with httpx.Client(timeout=settings.openrouter_timeout_seconds, headers=self._auth_headers()) as client:
            image_url = image_reference_url or self._upload_image_reference(client, ctx)
            payload = self._build_payload(prompt, image_url, duration_sec, aspect_ratio)
            submitted = self._submit(client, payload)
            request_id = submitted.get("request_id")
            status_payload = self._poll(client, submitted)
            response_payload = self._fetch_result(client, submitted)
            video_url = _extract_video_url(response_payload)
            if not video_url:
                raise ValueError(f"fal response did not include a video url: {list(response_payload)}")
            video_bytes = _download_video(client, video_url)
        duration_ms = round((time.perf_counter() - started_at) * 1000)
        logger.info(
            "fal AI-video scene completed",
            extra={"model": settings.ai_video_fal_model, "request_id": request_id, "duration_ms": duration_ms},
        )
        return AIVideoSceneResult(
            provider=f"fal:{settings.ai_video_fal_model}",
            scene_id=str(request_id) if request_id else None,
            status="generated",
            video_bytes=video_bytes,
            duration_sec=duration_sec,
            raw_response={
                "provider": self.provider_name,
                "model": settings.ai_video_fal_model,
                "request_id": request_id,
                "queue_status": status_payload.get("status"),
                "image_reference_used": bool(image_url),
                "duration_ms": duration_ms,
                "video_url": video_url,
            },
        )

    def _auth_headers(self) -> dict:
        return {"Authorization": f"Key {settings.ai_video_fal_key}"}

    def _upload_image_reference(self, client: httpx.Client, ctx: dict) -> str | None:
        image_bytes = ctx.get("image_reference_bytes")
        if not image_bytes:
            return None
        digest = hashlib.sha256(image_bytes).hexdigest()
        if digest in self._upload_cache:
            return self._upload_cache[digest]
        mime_type = str(ctx.get("image_reference_mime") or "image/jpeg")
        initiate = client.post(
            FAL_STORAGE_INITIATE_URL,
            json={"content_type": mime_type, "file_name": f"reference-{digest[:12]}.jpg"},
        )
        initiate.raise_for_status()
        initiate_payload = initiate.json()
        upload_url = initiate_payload.get("upload_url")
        file_url = initiate_payload.get("file_url")
        if not upload_url or not file_url:
            raise ValueError("fal storage initiate response missing upload_url/file_url")
        put_response = client.put(upload_url, content=image_bytes, headers={"Content-Type": mime_type})
        put_response.raise_for_status()
        self._upload_cache[digest] = file_url
        return file_url

    def _build_payload(self, prompt: str, image_url: str | None, duration_sec: float, aspect_ratio: str) -> dict:
        # Most fal video models share these field names; unsupported extras are surfaced
        # as a queue error and handled by the provider fallback.
        payload: dict = {"prompt": prompt, "duration": str(int(round(duration_sec)))}
        if image_url:
            payload["image_url"] = image_url
        if aspect_ratio:
            payload["aspect_ratio"] = aspect_ratio
        return payload

    def _submit(self, client: httpx.Client, payload: dict) -> dict:
        response = client.post(f"{FAL_QUEUE_BASE_URL}/{settings.ai_video_fal_model}", json=payload)
        response.raise_for_status()
        return response.json()

    def _poll(self, client: httpx.Client, submitted: dict) -> dict:
        status_url = submitted.get("status_url") or f"{FAL_QUEUE_BASE_URL}/{settings.ai_video_fal_model}/requests/{submitted.get('request_id')}/status"
        deadline = time.monotonic() + settings.ai_video_poll_timeout_seconds
        while True:
            response = client.get(status_url)
            response.raise_for_status()
            payload = response.json()
            status = str(payload.get("status") or "").upper()
            if status in TERMINAL_STATUSES:
                return payload
            if status in FAILED_STATUSES:
                raise ValueError(f"fal generation failed with status {status}: {payload.get('error') or payload}")
            if time.monotonic() > deadline:
                raise TimeoutError(f"fal generation timed out after {settings.ai_video_poll_timeout_seconds}s (last status {status})")
            time.sleep(settings.ai_video_poll_interval_seconds)

    def _fetch_result(self, client: httpx.Client, submitted: dict) -> dict:
        response_url = submitted.get("response_url") or f"{FAL_QUEUE_BASE_URL}/{settings.ai_video_fal_model}/requests/{submitted.get('request_id')}"
        response = client.get(response_url)
        response.raise_for_status()
        return response.json()


def _extract_video_url(response_payload: dict) -> str | None:
    video = response_payload.get("video")
    if isinstance(video, dict) and video.get("url"):
        return video["url"]
    videos = response_payload.get("videos")
    if isinstance(videos, list) and videos and isinstance(videos[0], dict) and videos[0].get("url"):
        return videos[0]["url"]
    if isinstance(response_payload.get("video_url"), str):
        return response_payload["video_url"]
    return None


def _download_video(client: httpx.Client, video_url: str) -> bytes:
    response = client.get(video_url, timeout=settings.video_render_timeout_seconds)
    response.raise_for_status()
    return response.content
