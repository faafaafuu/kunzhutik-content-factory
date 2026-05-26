from __future__ import annotations

from app.core.config import settings


REAL_TTS_PROVIDERS = {"elevenlabs", "yandex_speechkit", "yandex-speechkit", "yandex"}
REAL_AI_VIDEO_PROVIDERS = {"kling", "runway", "pika", "luma"}


def validate_generation_providers_ready() -> None:
    if settings.generation_profile.lower().strip() != "production":
        return

    missing: list[str] = []
    if settings.text_provider.lower().strip() != "openrouter":
        missing.append("TEXT_PROVIDER=openrouter")
    if not settings.openrouter_api_key:
        missing.append("OPENROUTER_API_KEY")
    if not settings.openrouter_text_model:
        missing.append("OPENROUTER_TEXT_MODEL")

    if settings.tts_provider.lower().strip() not in REAL_TTS_PROVIDERS:
        missing.append("TTS_PROVIDER=elevenlabs or yandex_speechkit")
    elif settings.tts_provider.lower().strip() == "elevenlabs":
        if not settings.elevenlabs_api_key:
            missing.append("ELEVENLABS_API_KEY")
        if not settings.elevenlabs_voice_id:
            missing.append("ELEVENLABS_VOICE_ID")
    else:
        if not settings.yandex_speechkit_api_key:
            missing.append("YANDEX_SPEECHKIT_API_KEY")
        if not settings.yandex_speechkit_folder_id:
            missing.append("YANDEX_SPEECHKIT_FOLDER_ID")

    video_mode = settings.video_mode.lower().strip()
    if video_mode == "ai_video":
        ai_video_provider = settings.ai_video_provider.lower().strip()
        if ai_video_provider not in REAL_AI_VIDEO_PROVIDERS:
            missing.append("AI_VIDEO_PROVIDER=kling or runway")
        elif ai_video_provider == "kling" and not settings.kling_api_key:
            missing.append("KLING_API_KEY")
        elif ai_video_provider == "runway" and not settings.runway_api_key:
            missing.append("RUNWAY_API_KEY")
    elif video_mode == "template":
        if settings.video_provider.lower().strip() != "creatomate":
            missing.append("VIDEO_PROVIDER=creatomate")
        if not settings.creatomate_api_key:
            missing.append("CREATOMATE_API_KEY")
        if not settings.creatomate_template_9_16:
            missing.append("CREATOMATE_TEMPLATE_9_16")
    else:
        missing.append("VIDEO_MODE=ai_video or template")

    if settings.enable_provider_fallback:
        missing.append("ENABLE_PROVIDER_FALLBACK=false")

    if missing:
        raise RuntimeError(
            "GENERATION_PROFILE=production requires real generation providers. "
            f"Missing or invalid config: {', '.join(missing)}"
        )
