from __future__ import annotations

from app.models.analysis_result import AnalysisResult
from app.models.character_profile import CharacterProfile
from app.providers.text_generation.factory import get_text_generation_provider
from app.providers.text_generation.schemas import GeneratedContent
from app.providers.vision.schemas import VisionAnalysisResult
from shared.enums import ContentPlatform, DraftKind

CONTENT_TARGETS: tuple[tuple[ContentPlatform, DraftKind], ...] = (
    (ContentPlatform.instagram, DraftKind.post),
    (ContentPlatform.vk, DraftKind.story),
    (ContentPlatform.yandex_maps, DraftKind.news),
)


def build_persona_drafts(character_profile: CharacterProfile | None, analysis: AnalysisResult) -> list[dict]:
    """One story-driven publication shared by every platform: a single LLM call,
    then per-platform draft rows carrying the same text (publication tasks need one draft per platform)."""
    provider = get_text_generation_provider()
    character = character_profile or _fallback_character_profile(analysis)
    vision_result = _analysis_to_vision_result(analysis)
    generated = provider.generate_content(
        analysis=vision_result,
        character_profile=character,
        platform="all",
        kind="story",
        context={
            "analysis_result_id": str(analysis.id),
            "project_id": str(analysis.project_id),
            "upload_id": str(analysis.upload_id),
        },
    )
    drafts: list[dict] = []
    for platform, kind in CONTENT_TARGETS:
        payload = _generated_to_content_draft_payload(generated, analysis.provider, platform=platform, kind=kind)
        payload["metadata_json"]["shared_story"] = True
        drafts.append(payload)
    return drafts


def _analysis_to_vision_result(analysis: AnalysisResult) -> VisionAnalysisResult:
    features = analysis.features_json or {}
    return VisionAnalysisResult(
        dish_name=analysis.dish_name or "Авторское блюдо дня",
        likely_ingredients=[str(item) for item in (analysis.ingredients or [])],
        plating=analysis.plating_style or "",
        mood=analysis.visual_mood or "",
        visual_features=[str(item) for item in features.get("visual_features", [])],
        quality_score=float(features.get("quality_score") or 0),
        warnings=[str(item) for item in features.get("warnings", [])],
        raw_response=analysis.raw_payload or {},
    )


def _generated_to_content_draft_payload(
    generated: GeneratedContent,
    analysis_provider: str,
    *,
    platform: ContentPlatform | None = None,
    kind: DraftKind | None = None,
) -> dict:
    hashtags_line = " ".join(generated.hashtags)
    long_text = generated.caption if not hashtags_line else f"{generated.caption}\n\n{hashtags_line}"
    return {
        "platform": platform or ContentPlatform(generated.platform),
        "kind": kind or DraftKind(generated.kind),
        "title": generated.hook,
        "caption": generated.caption,
        "cta": generated.cta or None,
        "short_text": generated.hook,
        "long_text": long_text,
        "script_text": generated.voice_script or None,
        "metadata_json": {
            "generation_mode": generated.raw_response.get("provider", "unknown"),
            "text_provider": generated.raw_response.get("provider", "unknown"),
            "analysis_provider": analysis_provider,
            "hashtags": generated.hashtags,
            "duration_sec": generated.duration_sec,
            "raw_response": generated.raw_response,
        },
    }


def _fallback_character_profile(analysis: AnalysisResult) -> CharacterProfile:
    return CharacterProfile(
        project_id=analysis.project_id,
        name="Кунжутик",
        appearance="Кунжутное зёрнышко в синем фартуке",
        tone="Дружелюбный, заботливый, с легким юмором",
        language="ru",
        voice_style="Приятный, энергичный, живой, без детскости",
        persona_prompt="Кунжутик пишет по-русски, тепло и живо, без кринжа и без детского тона.",
        is_default=True,
    )
