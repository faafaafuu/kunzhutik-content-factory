from __future__ import annotations

import contextlib
import subprocess
import tempfile
import wave
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.content_draft import ContentDraft
from app.models.media_asset import MediaAsset
from app.models.upload import Upload
from app.models.video_asset import VideoAsset
from app.models.voice_asset import VoiceAsset
from app.providers.tts.factory import get_tts_provider
from app.providers.tts.schemas import TTSResult
from app.providers.video_render.factory import get_video_render_provider
from app.providers.video_render.ffmpeg_fallback import VIDEO_HEIGHT, VIDEO_WIDTH, get_template_preset
from app.providers.video_render.schemas import RenderContent
from app.services.audit import log_event
from app.services.storage import download_bytes, upload_bytes
from shared.enums import AssetKind, PipelineStatus

VOICE_NAME = "ru"


def generate_media_assets_for_drafts(db: Session, upload: Upload, drafts: list[ContentDraft]) -> None:
    source_asset = next((asset for asset in upload.media_assets if asset.kind == AssetKind.source_photo), None)
    source_bytes = download_bytes(source_asset.storage_key) if source_asset else None
    for draft in drafts:
        script_text = draft.script_text or draft.long_text or draft.caption
        if not script_text:
            continue

        with tempfile.TemporaryDirectory(prefix="kunzhutik-render-") as tmp_dir_name:
            tmp_dir = Path(tmp_dir_name)
            voice_path = tmp_dir / "voice.wav"
            source_path = None

            if source_bytes and _looks_like_supported_image(source_bytes):
                source_suffix = Path(source_asset.file_name).suffix or ".bin"
                source_path = tmp_dir / f"source{source_suffix}"
                source_path.write_bytes(source_bytes)

            voice_asset, voice_path, tts_result, duration_seconds = _generate_voice_asset_for_draft_in_dir(
                db=db,
                upload=upload,
                draft=draft,
                script_text=script_text,
                tmp_dir=tmp_dir,
                actor="worker",
            )

            render_result = get_video_render_provider().render(
                source_image_url=str(source_path) if source_path else None,
                voice_asset_url=str(voice_path),
                content=_render_content_from_draft(draft),
                format="9:16",
                template_key=_get_template_preset(draft)["template_name"],
                context={"duration_seconds": str(duration_seconds)},
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
                duration_seconds=duration_seconds,
                metadata={
                    **render_result.raw_response,
                    "template_name": _get_template_preset(draft)["template_name"],
                    "platform": draft.platform.value,
                    "draft_kind": draft.kind.value,
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
                metadata={**render_result.raw_response, "template_name": _get_template_preset(draft)["template_name"], "source": "video_first_frame"},
            )
            video_asset = VideoAsset(
                project_id=upload.project_id,
                content_draft_id=draft.id,
                status=PipelineStatus.completed,
                template_name=_get_template_preset(draft)["template_name"],
                aspect_ratio="9:16",
                asset_id=video_media.id,
                preview_asset_id=preview_media.id,
            )
            db.add(video_asset)
            db.flush()

            log_event(
                db,
                upload.project_id,
                "upload",
                str(upload.id),
                "voice_asset.created",
                "worker",
                {"content_draft_id": str(draft.id), "voice_asset_id": str(voice_asset.id), "media_asset_id": str(voice_asset.asset_id)},
            )
            log_event(
                db,
                upload.project_id,
                "upload",
                str(upload.id),
                "video_asset.created",
                "worker",
                {"content_draft_id": str(draft.id), "video_asset_id": str(video_asset.id), "media_asset_id": str(video_media.id)},
            )


def generate_voice_asset_for_draft(db: Session, upload: Upload, draft: ContentDraft, *, actor: str = "worker") -> VoiceAsset:
    script_text = draft.script_text or draft.long_text or draft.caption
    if not script_text:
        raise ValueError(f"ContentDraft {draft.id} has no script text for TTS")
    with tempfile.TemporaryDirectory(prefix="kunzhutik-voice-") as tmp_dir_name:
        voice_asset, _, _, _ = _generate_voice_asset_for_draft_in_dir(
            db=db,
            upload=upload,
            draft=draft,
            script_text=script_text,
            tmp_dir=Path(tmp_dir_name),
            actor=actor,
        )
    return voice_asset


def _generate_voice_asset_for_draft_in_dir(
    db: Session,
    upload: Upload,
    draft: ContentDraft,
    script_text: str,
    tmp_dir: Path,
    *,
    actor: str,
) -> tuple[VoiceAsset, Path, TTSResult, Decimal]:
    tts_result = get_tts_provider().synthesize(script_text, {"voice_name": VOICE_NAME, "speed": "155"})
    voice_path = _write_tts_result(tts_result, tmp_dir)
    duration_seconds = _tts_duration_seconds(tts_result, voice_path)
    voice_media = _create_media_asset(
        db=db,
        upload=upload,
        draft=draft,
        kind=AssetKind.voice,
        file_path=voice_path,
        file_name=f"{draft.kind.value}-voice{voice_path.suffix}",
        mime_type=tts_result.mime_type,
        duration_seconds=duration_seconds,
        metadata={**tts_result.raw_response, "video_mode": settings.video_mode, "actor": actor},
    )
    voice_asset = VoiceAsset(
        project_id=upload.project_id,
        content_draft_id=draft.id,
        status=PipelineStatus.completed,
        provider=tts_result.provider,
        voice_name=tts_result.voice_id or VOICE_NAME,
        speaking_rate=Decimal("1.00"),
        asset_id=voice_media.id,
        transcript=script_text,
    )
    db.add(voice_asset)
    db.flush()
    return voice_asset, voice_path, tts_result, duration_seconds


def _create_media_asset(
    db: Session,
    upload: Upload,
    draft: ContentDraft,
    kind: AssetKind,
    file_path: Path,
    file_name: str,
    mime_type: str,
    width: int | None = None,
    height: int | None = None,
    duration_seconds: Decimal | None = None,
    metadata: dict | None = None,
) -> MediaAsset:
    storage_key = (
        f"projects/{upload.project.slug}/uploads/{upload.id}/drafts/{draft.id}/"
        f"{kind.value}-{uuid4().hex}{file_path.suffix.lower()}"
    )
    content = file_path.read_bytes()
    upload_bytes(storage_key, content, mime_type)

    media_asset = MediaAsset(
        project_id=upload.project_id,
        upload_id=upload.id,
        kind=kind,
        storage_key=storage_key,
        bucket_name=settings.s3_bucket,
        mime_type=mime_type,
        file_name=file_name,
        file_size=file_path.stat().st_size,
        width=width,
        height=height,
        duration_seconds=duration_seconds,
        metadata_json=metadata or {},
    )
    db.add(media_asset)
    db.flush()
    return media_asset


def _write_tts_result(tts_result: TTSResult, tmp_dir: Path) -> Path:
    suffix = _audio_suffix(tts_result.mime_type)
    output_path = tmp_dir / f"voice{suffix}"
    output_path.write_bytes(tts_result.audio_bytes)
    return output_path


def _tts_duration_seconds(tts_result: TTSResult, file_path: Path) -> Decimal:
    if tts_result.duration_sec is not None:
        return Decimal(str(tts_result.duration_sec)).quantize(Decimal("0.01"))
    if tts_result.mime_type == "audio/wav":
        return _read_wav_duration_seconds(file_path)
    return _probe_audio_duration_seconds(file_path)


def _audio_suffix(mime_type: str) -> str:
    if mime_type in {"audio/mpeg", "audio/mp3"}:
        return ".mp3"
    if mime_type == "audio/ogg":
        return ".ogg"
    return ".wav"


def _render_content_from_draft(draft: ContentDraft) -> RenderContent:
    return RenderContent(
        title=(draft.title or draft.caption).strip(),
        subtitle=(draft.cta or draft.short_text or draft.caption).strip(),
        platform=draft.platform.value,
        kind=draft.kind.value,
    )


def _write_render_output(content: bytes | None, source_url: str | None, output_path: Path) -> Path:
    if content:
        output_path.write_bytes(content)
        return output_path
    if source_url:
        with httpx.Client(timeout=settings.video_render_timeout_seconds) as client:
            response = client.get(source_url)
            response.raise_for_status()
            output_path.write_bytes(response.content)
            return output_path
    raise ValueError("Video render provider did not return required bytes or URL")


def _write_render_bytes(content: bytes | None, output_path: Path) -> Path:
    if not content:
        raise ValueError("Video render provider did not return required bytes")
    output_path.write_bytes(content)
    return output_path


def _read_wav_duration_seconds(file_path: Path) -> Decimal:
    with contextlib.closing(wave.open(str(file_path), "rb")) as wav_file:
        frame_count = wav_file.getnframes()
        sample_rate = wav_file.getframerate()
    if not sample_rate:
        return Decimal("0.00")
    duration = Decimal(frame_count) / Decimal(sample_rate)
    return duration.quantize(Decimal("0.01"))


def _probe_audio_duration_seconds(file_path: Path) -> Decimal:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(file_path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    return Decimal(result.stdout.strip() or "0").quantize(Decimal("0.01"))


def _looks_like_supported_image(content: bytes) -> bool:
    return any(
        content.startswith(signature)
        for signature in (
            b"\xff\xd8\xff",  # jpeg
            b"\x89PNG\r\n\x1a\n",  # png
            b"GIF87a",
            b"GIF89a",
            b"RIFF",  # webp container, validated loosely
        )
    )


def _get_template_preset(draft: ContentDraft) -> dict:
    return get_template_preset(draft.kind.value)
