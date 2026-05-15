from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.content_draft import ContentDraft
from app.models.media_asset import MediaAsset
from app.models.project import Project
from app.models.upload import Upload
from app.models.video_asset import VideoAsset
from app.models.voice_asset import VoiceAsset
from app.providers.video_render.ffmpeg_fallback import VIDEO_HEIGHT, VIDEO_WIDTH, get_template_preset
from app.providers.video_render.factory import get_video_render_provider
from app.services.audit import log_event
from app.services.media_generation import _create_media_asset, _looks_like_supported_image, _render_content_from_draft, _write_render_output
from app.services.storage import download_bytes
from shared.enums import AssetKind, PipelineStatus


def regenerate_video_asset(
    db: Session,
    video_asset_id: UUID,
    *,
    actor: str,
    reason: str | None = None,
) -> VideoAsset:
    previous = db.query(VideoAsset).filter(VideoAsset.id == video_asset_id).first()
    if not previous:
        raise HTTPException(status_code=404, detail="Video asset not found")
    draft = db.query(ContentDraft).filter(ContentDraft.id == previous.content_draft_id).first()
    if not draft:
        raise HTTPException(status_code=409, detail="Video asset has no content draft")
    upload = db.query(Upload).filter(Upload.id == draft.upload_id).first()
    project = db.query(Project).filter(Project.id == draft.project_id).first()
    if not upload or not project:
        raise HTTPException(status_code=409, detail="Draft upload or project not found")
    upload.project = project

    voice_asset = (
        db.query(VoiceAsset)
        .filter(VoiceAsset.content_draft_id == draft.id, VoiceAsset.asset_id.is_not(None))
        .order_by(VoiceAsset.created_at.desc())
        .first()
    )
    if not voice_asset:
        raise HTTPException(status_code=409, detail="Content draft has no voice asset")
    voice_media = db.query(MediaAsset).filter(MediaAsset.id == voice_asset.asset_id).first()
    if not voice_media:
        raise HTTPException(status_code=409, detail="Voice media asset not found")

    source_asset = (
        db.query(MediaAsset)
        .filter(MediaAsset.upload_id == upload.id, MediaAsset.kind == AssetKind.source_photo)
        .order_by(MediaAsset.created_at.asc())
        .first()
    )
    with tempfile.TemporaryDirectory(prefix="kunzhutik-video-regenerate-") as tmp_dir_name:
        tmp_dir = Path(tmp_dir_name)
        voice_path = tmp_dir / f"voice{_suffix_for_mime(voice_media.mime_type)}"
        voice_path.write_bytes(download_bytes(voice_media.storage_key))
        source_path = None
        if source_asset:
            source_bytes = download_bytes(source_asset.storage_key)
            if _looks_like_supported_image(source_bytes):
                source_path = tmp_dir / f"source{Path(source_asset.file_name).suffix or '.bin'}"
                source_path.write_bytes(source_bytes)

        preset = get_template_preset(draft.kind.value)
        render_result = get_video_render_provider().render(
            source_image_url=str(source_path) if source_path else None,
            voice_asset_url=str(voice_path),
            content=_render_content_from_draft(draft),
            format=previous.aspect_ratio,
            template_key=preset["template_name"],
            context={"duration_seconds": str(voice_media.duration_seconds or "8")},
        )
        video_path = _write_render_output(render_result.video_bytes, render_result.video_url, tmp_dir / "video.mp4")
        preview_path = _write_render_output(render_result.preview_bytes, render_result.preview_url, tmp_dir / "preview.jpg")

        video_media = _create_media_asset(
            db=db,
            upload=upload,
            draft=draft,
            kind=AssetKind.video,
            file_path=video_path,
            file_name=f"{draft.kind.value}-video.mp4",
            mime_type="video/mp4",
            width=VIDEO_WIDTH,
            height=VIDEO_HEIGHT,
            duration_seconds=voice_media.duration_seconds,
            metadata={
                **render_result.raw_response,
                "template_name": preset["template_name"],
                "regenerated_from_video_asset_id": str(previous.id),
                "regenerate_reason": reason,
            },
        )
        preview_media = _create_media_asset(
            db=db,
            upload=upload,
            draft=draft,
            kind=AssetKind.preview,
            file_path=preview_path,
            file_name=f"{draft.kind.value}-preview.jpg",
            mime_type="image/jpeg",
            width=VIDEO_WIDTH,
            height=VIDEO_HEIGHT,
            metadata={
                **render_result.raw_response,
                "template_name": preset["template_name"],
                "source": "video_first_frame",
                "regenerated_from_video_asset_id": str(previous.id),
            },
        )

    video_asset = VideoAsset(
        project_id=draft.project_id,
        content_draft_id=draft.id,
        status=PipelineStatus.completed,
        template_name=preset["template_name"],
        aspect_ratio=previous.aspect_ratio,
        asset_id=video_media.id,
        preview_asset_id=preview_media.id,
    )
    db.add(video_asset)
    db.flush()
    log_event(
        db,
        draft.project_id,
        "upload",
        str(draft.upload_id),
        "video.regenerated",
        actor,
        {
            "previous_video_asset_id": str(previous.id),
            "new_video_asset_id": str(video_asset.id),
            "media_asset_id": str(video_media.id),
            "preview_asset_id": str(preview_media.id),
            "content_draft_id": str(draft.id),
            "provider": render_result.provider,
            "reason": reason,
        },
    )
    db.commit()
    db.refresh(video_asset)
    return video_asset


def _suffix_for_mime(mime_type: str) -> str:
    if mime_type in {"audio/mpeg", "audio/mp3"}:
        return ".mp3"
    if mime_type == "audio/ogg":
        return ".ogg"
    return ".wav"
