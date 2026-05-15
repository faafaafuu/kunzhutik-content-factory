from app.providers.video_render.ffmpeg_fallback import FfmpegVideoRenderProvider


class MockVideoRenderProvider(FfmpegVideoRenderProvider):
    provider_name = "ffmpeg"
