from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from app.providers.video_render.base import VideoRenderProvider
from app.providers.video_render.schemas import RenderContent, VideoRenderResult

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
VIDEO_WIDTH = 720
VIDEO_HEIGHT = 1280
VIDEO_FPS = 24
MASCOT_ASSET_PATH = Path(__file__).resolve().parents[2] / "web" / "assets" / "kunzhutik-mascot.svg"

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


class FfmpegVideoRenderProvider(VideoRenderProvider):
    provider_name = "ffmpeg"

    def render(
        self,
        source_image_url: str | None,
        voice_asset_url: str | None,
        content: RenderContent,
        format: str,
        template_key: str,
        context: dict | None = None,
    ) -> VideoRenderResult:
        if not voice_asset_url:
            raise ValueError("voice_asset_url is required for ffmpeg render")
        ctx = context or {}
        duration_seconds = str(ctx.get("duration_seconds") or "8")
        with tempfile.TemporaryDirectory(prefix="kunzhutik-video-") as tmp_dir_name:
            tmp_dir = Path(tmp_dir_name)
            audio_path = Path(voice_asset_url)
            source_path = Path(source_image_url) if source_image_url else None
            video_path = tmp_dir / "video.mp4"
            preview_path = tmp_dir / "preview.jpg"
            try:
                _render_vertical_video(content, source_path, audio_path, video_path, duration_seconds)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                _render_vertical_video(content, None, audio_path, video_path, duration_seconds)
            _render_preview_frame(video_path, preview_path)
            return VideoRenderResult(
                video_bytes=video_path.read_bytes(),
                preview_bytes=preview_path.read_bytes(),
                provider=self.provider_name,
                status="completed",
                raw_response={
                    "provider": self.provider_name,
                    "template_key": template_key,
                    "format": format,
                    "width": VIDEO_WIDTH,
                    "height": VIDEO_HEIGHT,
                },
            )


def get_template_preset(kind: str) -> dict:
    return TEMPLATE_PRESETS.get(kind, TEMPLATE_PRESETS["story"])


def _render_vertical_video(
    content: RenderContent,
    source_path: Path | None,
    audio_path: Path,
    output_path: Path,
    duration_seconds: str,
) -> None:
    preset = get_template_preset(content.kind)
    mascot_text = _escape_drawtext("Кунжутик")
    title_text = _escape_drawtext(content.title.strip()[:72])
    subtitle_text = _escape_drawtext(content.subtitle.strip()[:88])
    subtitle_color = "white" if content.kind != "story" else "#27140d"
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
        input_args = ["-loop", "1", "-i", str(source_path), "-loop", "1", "-i", str(MASCOT_ASSET_PATH)]
        video_filter = (
            f"[0:v]scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},zoompan=z='min(zoom+0.0009,1.12)':x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':d=1:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={VIDEO_FPS},setsar=1,format=yuv420p[bg];"
            f"[1:v]scale={preset['mascot_scale']}:-1,format=rgba,colorchannelmixer=aa=0.96[mascot];"
            f"[bg][mascot]overlay=x={preset['mascot_x']}:y={preset['mascot_y']}[composed];"
            f"[composed]{draw_filters}[v]"
        )
    else:
        input_args = ["-f", "lavfi", "-i", f"color=c={preset['background']}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:r={VIDEO_FPS}", "-loop", "1", "-i", str(MASCOT_ASSET_PATH)]
        video_filter = (
            f"[0:v]format=yuv420p[bg];"
            f"[1:v]scale={preset['mascot_scale']}:-1,format=rgba,colorchannelmixer=aa=0.98[mascot];"
            f"[bg][mascot]overlay=x={preset['mascot_x']}:y={preset['mascot_y']}[composed];"
            f"[composed]{draw_filters}[v]"
        )
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
            "2:a",
            "-t",
            duration_seconds,
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
        ["ffmpeg", "-y", "-i", str(video_path), "-frames:v", "1", str(preview_path)],
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )


def _escape_drawtext(value: str) -> str:
    return (
        value.replace("\\", r"\\")
        .replace(":", r"\:")
        .replace(",", r"\,")
        .replace("'", r"\'")
        .replace("%", r"\%")
        .replace("\n", r"\n")
    )
