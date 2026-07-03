from __future__ import annotations

import json

from app.models.character_profile import CharacterProfile
from app.providers.vision.schemas import VisionAnalysisResult


PERSONA_RULES = """
Кунжутик — маленькое кунжутное зернышко в синем фартуке.
Тон: дружелюбный, заботливый, с легким юмором.
Не писать кринжово.
Не использовать детский тон.
Не перебарщивать с эмодзи.
Язык: русский.
""".strip()


PLATFORM_RULES = {
    "instagram:post": "Пост: цепкий hook, аппетитный caption, мягкий CTA, 3-6 релевантных hashtag.",
    "instagram:reel": "Reel: короткий hook, динамичный voice_script до 15 секунд, ясный CTA.",
    "instagram:story": "Story: очень короткий текст, один простой CTA.",
    "vk:post": "VK пост: чуть более разговорно, без перегруза hashtag.",
    "vk:clip": "VK клип: короткий сценарий до 15 секунд, живой темп.",
    "vk:story": "VK story: коротко, понятно, с вопросом или действием.",
    "yandex_maps:news": "Новость Яндекс.Карт: информативно, без агрессивной рекламы, больше пользы.",
    "yandex_maps:photo_caption": "Подпись к фото Яндекс.Карт: коротко, ясно, без hashtag.",
}


def build_system_prompt(character_profile: CharacterProfile) -> str:
    return "\n\n".join(
        [
            "Ты пишешь ресторанный food-контент от имени персонажа.",
            PERSONA_RULES,
            f"Профиль персонажа из базы:\n{character_profile.persona_prompt}",
            "Верни только JSON без markdown.",
        ]
    )


def build_scene_plan_system_prompt(character_prompt: str, style_prompt: str) -> str:
    return "\n\n".join(
        [
            "Ты — режиссер коротких вертикальных food-роликов (Reels/Clips) для ресторана.",
            PERSONA_RULES,
            f"Требование к персонажу в каждой сцене:\n{character_prompt}",
            f"Визуальный стиль:\n{style_prompt}",
            "Верни только JSON без markdown.",
        ]
    )


def build_scene_plan_user_prompt(
    draft_context: dict,
    scenes_count: int,
    total_duration_sec: int,
    context: dict | None = None,
) -> str:
    payload = {
        "draft": draft_context,
        "scenes_count": scenes_count,
        "total_duration_sec": total_duration_sec,
        "context": context or {},
        "scene_json_fields": {
            "scene_number": "int, с 1",
            "duration_sec": "int, секунды сцены, сумма примерно равна total_duration_sec",
            "visual_prompt": "детальный prompt сцены для image-to-video генерации: что делает Кунжутик, как показано блюдо, движение камеры, свет; на русском или английском",
            "voice_text": "фраза закадрового голоса для этой сцены, русский, короткая",
            "subtitle_text": "субтитр до 90 символов, русский",
            "camera": "краткое описание движения камеры, английский",
            "emotion": "эмоция персонажа одним словом, английский",
        },
    }
    return (
        "Составь план сцен для одного вертикального ролика о блюде. "
        f"Ровно {scenes_count} сцен: хук в первой, показ блюда в середине, CTA в последней. "
        "Каждая сцена должна быть самодостаточным prompt для видео-генерации по опорному фото блюда. "
        'Верни строго JSON вида {"scenes": [ ... ]} по scene_json_fields.\n\n'
        f"{json.dumps(payload, ensure_ascii=False)}"
    )


def build_user_prompt(
    analysis: VisionAnalysisResult,
    platform: str,
    kind: str,
    context: dict | None = None,
) -> str:
    platform_rule = PLATFORM_RULES.get(f"{platform}:{kind}", "Соблюдай формат платформы и тип публикации.")
    payload = {
        "platform": platform,
        "kind": kind,
        "platform_rule": platform_rule,
        "analysis": analysis.model_dump(exclude={"raw_response"}),
        "context": context or {},
        "required_json_fields": [
            "platform",
            "kind",
            "hook",
            "caption",
            "cta",
            "hashtags",
            "voice_script",
            "duration_sec",
        ],
    }
    return (
        "Сгенерируй контент для указанной платформы. "
        "Пиши от лица Кунжутика, но без детского тона и без кринжа. "
        "Верни строго JSON по required_json_fields.\n\n"
        f"{json.dumps(payload, ensure_ascii=False)}"
    )
