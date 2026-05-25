from __future__ import annotations

import subprocess
import tempfile
import textwrap
from pathlib import Path
from uuid import uuid4

from app.providers.ai_video.base import AIVideoProvider
from app.providers.ai_video.schemas import AIVideoSceneResult
from app.providers.video_render.ffmpeg_fallback import FONT_PATH, VIDEO_FPS, VIDEO_HEIGHT, VIDEO_WIDTH


class MockAIVideoProvider(AIVideoProvider):
    provider_name = "mock-ai-video"

    def generate_scene(
        self,
        prompt: str,
        image_reference_url: str | None,
        character_reference_url: str | None,
        duration_sec: float,
        aspect_ratio: str,
        context: dict | None = None,
    ) -> AIVideoSceneResult:
        ctx = context or {}
        scene_number = int(ctx.get("scene_number") or 1)
        subtitle = str(ctx.get("subtitle_text") or prompt)
        with tempfile.TemporaryDirectory(prefix="kunzhutik-ai-scene-") as tmp_dir_name:
            output_path = Path(tmp_dir_name) / "scene.mp4"
            _render_mock_scene(output_path, subtitle, scene_number, duration_sec)
            return AIVideoSceneResult(
                provider=self.provider_name,
                scene_id=f"mock-scene-{uuid4().hex[:12]}",
                status="generated",
                video_bytes=output_path.read_bytes(),
                duration_sec=duration_sec,
                raw_response={
                    "provider": self.provider_name,
                    "mode": "mock",
                    "scene_number": scene_number,
                    "aspect_ratio": aspect_ratio,
                    "image_reference_url": image_reference_url,
                    "character_reference_url": character_reference_url,
                },
            )


def _render_mock_scene(output_path: Path, subtitle: str, scene_number: int, duration_sec: float) -> None:
    color = ["#244a6b", "#4c2f6f", "#6b3b24", "#2f664e"][(scene_number - 1) % 4]
    lines = textwrap.wrap(" ".join(subtitle.split()), width=25, max_lines=3, placeholder="…")
    draw = [
        "format=yuv420p",
        "vignette=PI/5",
        f"drawtext=fontfile={FONT_PATH}:text='Кунжутик / сцена {scene_number}':fontcolor=#ffd08a:fontsize=34:x=44:y=70",
        "drawbox=x=36:y=930:w=648:h=250:color=black@0.35:t=fill",
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='3D scene placeholder':fontcolor=white@0.62:fontsize=24:x=44:y=1200",
    ]
    for index, line in enumerate(lines):
        escaped = _escape_drawtext(line)
        draw.append(f"drawtext=fontfile={FONT_PATH}:text='{escaped}':fontcolor=white:fontsize=38:x=54:y={980 + index * 48}")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c={color}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:r={VIDEO_FPS}",
            "-t",
            str(duration_sec),
            "-vf",
            ",".join(draw),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=40,
    )


def _escape_drawtext(value: str) -> str:
    return value.replace("\\", r"\\").replace(":", r"\:").replace(",", r"\,").replace("'", r"\'").replace("%", r"\%")
