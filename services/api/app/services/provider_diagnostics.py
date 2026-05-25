from __future__ import annotations

from app.core.config import settings
from app.schemas.provider_diagnostics import ProviderDiagnostic


def get_provider_diagnostics() -> list[ProviderDiagnostic]:
    fallback = settings.enable_provider_fallback
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
        fallback_enabled=fallback,
        missing_env=missing,
        notes=notes,
    )
