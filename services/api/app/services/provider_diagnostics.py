from __future__ import annotations

from app.core.config import settings
from app.schemas.provider_diagnostics import ProviderDiagnostic
from app.services.generation_readiness import REAL_TTS_PROVIDERS


def get_provider_diagnostics() -> list[ProviderDiagnostic]:
    fallback = settings.enable_provider_fallback
    production = settings.generation_profile.lower().strip() == "production"
    return [
        _diagnostic(
            area="vision",
            selected=settings.vision_provider,
            local={"mock", "fallback"},
            required={
                "openrouter": {
                    "OPENROUTER_API_KEY": settings.openrouter_api_key,
                    "OPENROUTER_VISION_MODEL": settings.openrouter_vision_model,
                }
            },
            fallback=fallback,
            production_ready=True,
            notes=["OpenRouter vision requires a multimodal model."],
        ),
        _diagnostic(
            area="text_generation",
            selected=settings.text_provider,
            local={"mock", "fallback"},
            required={
                "openrouter": {
                    "OPENROUTER_API_KEY": settings.openrouter_api_key,
                    "OPENROUTER_TEXT_MODEL": settings.openrouter_text_model,
                }
            },
            fallback=fallback,
            production_ready=settings.text_provider.lower().strip() == "openrouter"
            and bool(settings.openrouter_api_key)
            and bool(settings.openrouter_text_model)
            and not fallback,
            notes=["Persona copy uses the Kunzhutik prompt layer before validation."],
        ),
        _diagnostic(
            area="tts",
            selected=settings.tts_provider,
            local={"mock", "espeak", "espeak-ng", "fallback"},
            required={
                "elevenlabs": {
                    "ELEVENLABS_API_KEY": settings.elevenlabs_api_key,
                    "ELEVENLABS_VOICE_ID": settings.elevenlabs_voice_id,
                },
                "yandex_speechkit": {
                    "YANDEX_SPEECHKIT_API_KEY": settings.yandex_speechkit_api_key,
                    "YANDEX_SPEECHKIT_FOLDER_ID": settings.yandex_speechkit_folder_id,
                },
                "yandex": {
                    "YANDEX_SPEECHKIT_API_KEY": settings.yandex_speechkit_api_key,
                    "YANDEX_SPEECHKIT_FOLDER_ID": settings.yandex_speechkit_folder_id,
                },
            },
            fallback=fallback,
            production_ready=_tts_production_ready() and not fallback,
            notes=["Local mock uses espeak-ng in the API/worker image."],
        ),
        _diagnostic(
            area="video_render",
            selected=settings.video_provider,
            local={"ffmpeg", "mock", "fallback"},
            required={
                "creatomate": {
                    "CREATOMATE_API_KEY": settings.creatomate_api_key,
                    "CREATOMATE_TEMPLATE_9_16": settings.creatomate_template_9_16,
                }
            },
            fallback=fallback,
            production_ready=settings.video_provider.lower().strip() == "creatomate"
            and bool(settings.creatomate_api_key)
            and bool(settings.creatomate_template_9_16)
            and not fallback,
            notes=["Creatomate can return external URLs; the pipeline downloads them into object storage."],
        ),
        _diagnostic(
            area="publishing",
            selected=settings.publisher_provider,
            local={"mock", "manual", "manual_package", "instagram_manual", "yandex_manual"},
            required={
                "vk": {
                    "VK_ACCESS_TOKEN": settings.vk_access_token,
                    "VK_GROUP_ID": settings.vk_group_id,
                }
            },
            fallback=fallback,
            production_ready=not production or settings.publisher_provider.lower().strip() in {"vk", "manual", "manual_package"},
            notes=["When PUBLISHER_PROVIDER=vk, Instagram/Yandex tasks use manual package providers."],
        ),
    ]


def _diagnostic(
    *,
    area: str,
    selected: str,
    local: set[str],
    required: dict[str, dict[str, str | None]],
    fallback: bool,
    production_ready: bool,
    notes: list[str],
) -> ProviderDiagnostic:
    normalized = selected.lower().strip()
    requirements = required.get(normalized, {})
    missing = [name for name, value in requirements.items() if not value]
    configured = normalized in local or not missing
    effective = normalized if configured else "fallback" if fallback else "unconfigured"
    return ProviderDiagnostic(
        area=area,
        selected_provider=normalized,
        effective_provider=effective,
        configured=configured,
        production_ready=production_ready,
        fallback_enabled=fallback,
        missing_env=missing,
        notes=notes,
    )


def _tts_production_ready() -> bool:
    provider = settings.tts_provider.lower().strip()
    if provider not in REAL_TTS_PROVIDERS:
        return False
    if provider == "elevenlabs":
        return bool(settings.elevenlabs_api_key and settings.elevenlabs_voice_id)
    return bool(settings.yandex_speechkit_api_key and settings.yandex_speechkit_folder_id)
