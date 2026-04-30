from __future__ import annotations

import contextlib
import subprocess
import tempfile
import wave
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.content_draft import ContentDraft
from app.models.media_asset import MediaAsset
from app.models.upload import Upload
from app.models.video_asset import VideoAsset
from app.models.voice_asset import VoiceAsset
from app.services.audit import log_event
from app.services.storage import download_bytes, upload_bytes
from shared.enums import AssetKind, PipelineStatus

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
VIDEO_WIDTH = 720
VIDEO_HEIGHT = 1280
VIDEO_FPS = 24
VOICE_PROVIDER = "espeak-ng"
VOICE_NAME = "ru"
MASCOT_ASSET_PATH = Path(__file__).resolve().parents[1] / "web" / "assets" / "kunzhutik-mascot.svg"

TEMPLATE_PRESETS = {
    "post": {
        "template_name": "mascot_reel_menu_v2",
        "background": "#4b2416",
        "top_box": "drawbox=x=28:y=34:w=664:h=170:color=#2b120d@0.58:t=fill",
        "bottom_box": "drawbox=x=28:y=980:w=664:h=228:color=#1f0f0b@0.48:t=fill",
        "title_size": 38,
        "subtitle_size": 31,
        "title_y": 110,
        "subtitle_y": 1060,
        "mascot_scale": 230,
        "mascot_x": "W-w-26",
        "mascot_y": "H-h-356+20*sin(2*PI*t/3)",
        "cta_label": "Рилс / хедлайн",
    },
    "story": {
        "template_name": "mascot_story_flash_v2",
        "background": "#663119",
        "top_box": "drawbox=x=34:y=52:w=652:h=148:color=#ffffff@0.14:t=fill",
        "bottom_box": "drawbox=x=34:y=1002:w=652:h=194:color=#f5dfc0@0.18:t=fill",
        "title_size": 42,
        "subtitle_size": 30,
        "title_y": 102,
        "subtitle_y": 1052,
        "mascot_scale": 250,
        "mascot_x": "W-w-14",
        "mascot_y": "H-h-216+12*sin(2*PI*t/2.4)",
        "cta_label": "Story / call to action",
    },
    "news": {
        "template_name": "mascot_local_news_v2",
        "background": "#203a43",
        "top_box": "drawbox=x=24:y=44:w=672:h=182:color=#09141c@0.52:t=fill",
        "bottom_box": "drawbox=x=24:y=950:w=672:h=248:color=#081018@0.54:t=fill",
        "title_size": 36,
        "subtitle_size": 29,
        "title_y": 118,
        "subtitle_y": 1024,
        "mascot_scale": 208,
        "mascot_x": "36",
        "mascot_y": "H-h-304+14*sin(2*PI*t/4.2)",
        "cta_label": "Local / maps news",
    },
}


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
            video_path = tmp_dir / "video.mp4"
            preview_path = tmp_dir / "preview.jpg"
            source_path = None

            if source_bytes and _looks_like_supported_image(source_bytes):
                source_suffix = Path(source_asset.file_name).suffix or ".bin"
                source_path = tmp_dir / f"source{source_suffix}"
                source_path.write_bytes(source_bytes)

            _render_voice_track(script_text, voice_path)
            duration_seconds = _read_wav_duration_seconds(voice_path)

            try:
                _render_vertical_video(
                    draft=draft,
                    source_path=source_path,
                    audio_path=voice_path,
                    output_path=video_path,
                    duration_seconds=duration_seconds,
                )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                _render_vertical_video(
                    draft=draft,
                    source_path=None,
                    audio_path=voice_path,
                    output_path=video_path,
                    duration_seconds=duration_seconds,
                )

            _render_preview_frame(video_path, preview_path)

            voice_media = _create_media_asset(
                db=db,
                upload=upload,
                draft=draft,
                kind=AssetKind.voice,
                file_path=voice_path,
                file_name=f"{draft.kind.value}-voice.wav",
                mime_type="audio/wav",
                duration_seconds=duration_seconds,
                metadata={"provider": VOICE_PROVIDER, "voice_name": VOICE_NAME},
            )
            voice_asset = VoiceAsset(
                project_id=upload.project_id,
                content_draft_id=draft.id,
                status=PipelineStatus.completed,
                provider=VOICE_PROVIDER,
                voice_name=VOICE_NAME,
                speaking_rate=Decimal("1.00"),
                asset_id=voice_media.id,
                transcript=script_text,
            )
            db.add(voice_asset)
            db.flush()

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
                metadata={"template_name": _get_template_preset(draft)["template_name"], "source": "video_first_frame"},
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
                {"content_draft_id": str(draft.id), "voice_asset_id": str(voice_asset.id), "media_asset_id": str(voice_media.id)},
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


def _render_voice_track(script_text: str, output_path: Path) -> None:
    subprocess.run(
        [
            "espeak-ng",
            "-v",
            VOICE_NAME,
            "-s",
            "155",
            "-w",
            str(output_path),
            script_text,
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )


def _render_vertical_video(
    draft: ContentDraft,
    source_path: Path | None,
    audio_path: Path,
    output_path: Path,
    duration_seconds: Decimal,
) -> None:
    preset = _get_template_preset(draft)
    mascot_text = _escape_drawtext("Кунжутик")
    title_text = _escape_drawtext((draft.title or draft.caption).strip()[:72])
    subtitle_text = _escape_drawtext((draft.cta or draft.short_text or draft.caption).strip()[:88])
    subtitle_color = "white" if draft.kind.value != "story" else "#27140d"
    draw_filters = ",".join(
        [
            preset["top_box"],
            preset["bottom_box"],
            f"drawtext=fontfile={FONT_PATH}:text='{mascot_text}':fontcolor=white:fontsize=40:x=54:y=62",
            f"drawtext=fontfile={FONT_PATH}:text='{_escape_drawtext(preset['cta_label'])}':fontcolor=#ffd08a:fontsize=24:x=54:y=88",
            f"drawtext=fontfile={FONT_PATH}:text='{title_text}':fontcolor=white:fontsize={preset['title_size']}:x=54:y={preset['title_y']}",
            f"drawtext=fontfile={FONT_PATH}:text='{subtitle_text}':fontcolor={subtitle_color}:fontsize={preset['subtitle_size']}:x=54:y={preset['subtitle_y']}",
        ]
    )

    if source_path and source_path.exists():
        input_args = [
            "-loop",
            "1",
            "-i",
            str(source_path),
            "-loop",
            "1",
            "-i",
            str(MASCOT_ASSET_PATH),
        ]
        video_filter = (
            f"[0:v]scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},zoompan=z='min(zoom+0.0009,1.12)':x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':d=1:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={VIDEO_FPS},setsar=1,format=yuv420p[bg];"
            f"[1:v]scale={preset['mascot_scale']}:-1,format=rgba,colorchannelmixer=aa=0.96[mascot];"
            f"[bg][mascot]overlay=x={preset['mascot_x']}:y={preset['mascot_y']}[composed];"
            f"[composed]{draw_filters}[v]"
        )
        audio_map = "2:a"
    else:
        input_args = [
            "-f",
            "lavfi",
            "-i",
            f"color=c={preset['background']}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:r={VIDEO_FPS}",
            "-loop",
            "1",
            "-i",
            str(MASCOT_ASSET_PATH),
        ]
        video_filter = (
            f"[0:v]format=yuv420p[bg];"
            f"[1:v]scale={preset['mascot_scale']}:-1,format=rgba,colorchannelmixer=aa=0.98[mascot];"
            f"[bg][mascot]overlay=x={preset['mascot_x']}:y={preset['mascot_y']}[composed];"
            f"[composed]{draw_filters}[v]"
        )
        audio_map = "2:a"

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            *input_args,
            "-i",
            str(audio_path),
            "-filter_complex",
            video_filter,
            "-map",
            "[v]",
            "-map",
            audio_map,
            "-t",
            str(duration_seconds),
            "-r",
            str(VIDEO_FPS),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _render_preview_frame(video_path: Path, preview_path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            str(preview_path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )


def _read_wav_duration_seconds(file_path: Path) -> Decimal:
    with contextlib.closing(wave.open(str(file_path), "rb")) as wav_file:
        frame_count = wav_file.getnframes()
        sample_rate = wav_file.getframerate()
    if not sample_rate:
        return Decimal("0.00")
    duration = Decimal(frame_count) / Decimal(sample_rate)
    return duration.quantize(Decimal("0.01"))


def _escape_drawtext(value: str) -> str:
    return (
        value.replace("\\", r"\\")
        .replace(":", r"\:")
        .replace(",", r"\,")
        .replace("'", r"\'")
        .replace("%", r"\%")
        .replace("\n", r"\n")
    )


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
    return TEMPLATE_PRESETS.get(draft.kind.value, TEMPLATE_PRESETS["story"])
