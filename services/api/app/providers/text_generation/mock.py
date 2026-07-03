from __future__ import annotations

from app.models.character_profile import CharacterProfile
from app.providers.text_generation.base import TextGenerationProvider
from app.providers.text_generation.schemas import GeneratedContent, GeneratedScenePlan
from app.providers.vision.schemas import VisionAnalysisResult

SCENE_STORY = [
    ("Хук", "Кунжутик как главный 3D-герой входит в кадр рядом с блюдом, замечает его, оживляется и реагирует выразительной мимикой. Не иконка, не стикер, персонаж занимает центр сцены.", "cinematic push-in, shallow depth of field", "curious"),
    ("Эмоция", "Кунжутик делает короткий дружелюбный жест, вдохновленно реагирует на аромат, вокруг видны пар, свет и аппетитные детали еды. Камера мягко движется вокруг героя.", "medium orbit, warm commercial lighting", "delighted"),
    ("Показ блюда", "Кунжутик показывает блюдо как ведущий мини-ролика: крупные планы текстуры, соус, свежесть, хруст, затем реакция персонажа в том же 3D-стиле.", "macro food shot with hero reaction cutaway", "proud"),
    ("CTA", "Финальная 3D-сцена: Кунжутик рядом с блюдом смотрит в камеру, энергично приглашает попробовать, брендовый CTA появляется в конце.", "front hero shot, gentle dolly-in", "friendly"),
]


class MockTextGenerationProvider(TextGenerationProvider):
    provider_name = "mock-text-v1"

    def generate_scene_plan(
        self,
        draft_context: dict,
        character_prompt: str,
        style_prompt: str,
        scenes_count: int,
        total_duration_sec: int,
        context: dict | None = None,
    ) -> GeneratedScenePlan:
        base_duration = max(5, round(total_duration_sec / scenes_count))
        cta = draft_context.get("cta") or ""
        title_line = (draft_context.get("title") or draft_context.get("caption") or "")[:90]
        voice_text = (draft_context.get("script_text") or draft_context.get("caption") or "")[:240]
        scenes = []
        for index in range(scenes_count):
            title, visual, camera, emotion = SCENE_STORY[index % len(SCENE_STORY)]
            subtitle = cta if index == scenes_count - 1 and cta else title_line
            scenes.append(
                {
                    "scene_number": index + 1,
                    "duration_sec": base_duration,
                    "visual_prompt": f"{title}: {visual} Стиль: {style_prompt}",
                    "voice_text": voice_text,
                    "subtitle_text": subtitle,
                    "camera": camera,
                    "emotion": emotion,
                    "status": "queued",
                }
            )
        return GeneratedScenePlan(provider=self.provider_name, scenes=scenes, raw_response={"provider": self.provider_name, "mode": "mock"})

    def generate_content(
        self,
        analysis: VisionAnalysisResult,
        character_profile: CharacterProfile,
        platform: str,
        kind: str,
        context: dict | None = None,
    ) -> GeneratedContent:
        dish_name = analysis.dish_name or "наше блюдо"
        mood = analysis.mood or "аппетитное настроение"
        plating = analysis.plating or "красивая подача"
        ingredient_line = ", ".join(analysis.likely_ingredients[:3]) if analysis.likely_ingredients else "секретные вкусности"

        if platform == "all":
            fact = (
                f"Мало кто знает, но у блюда вроде «{dish_name}» всегда есть своя история: "
                f"{ingredient_line} здесь не случайно — именно это сочетание делает вкус узнаваемым."
            )
            return GeneratedContent(
                platform=platform,
                kind=kind,
                hook=f"Одна деталь про {dish_name}, которую вы могли не замечать",
                caption=f"{fact} Я, Кунжутик, проверил лично: {plating.lower() if plating else 'подача'} и {mood.lower() if mood else 'настроение'} — всё на месте.",
                cta="Приходите попробовать, пока горячее — расскажу остальное за столом.",
                hashtags=["#кунжутик", "#вкусно", "#историяблюда"],
                voice_script=f"Знаете, что прячется в {dish_name}? {ingredient_line}. Смотрите, какая подача — и да, это надо пробовать.",
                duration_sec=15,
                raw_response={"provider": self.provider_name, "mode": "mock", "story": True},
            )

        if platform == "instagram":
            return GeneratedContent(
                platform=platform,
                kind=kind,
                hook=f"{dish_name} от Кунжутика",
                caption=f"Я, Кунжутик, уже тут и шепчу: {dish_name} выглядит так, будто тарелка решила устроить праздник вкуса.",
                cta="Заглядывайте в гости и пробуйте, пока я не съел взглядом всё сам.",
                hashtags=["#кунжутик", "#вкусно", "#food"],
                voice_script=f"Я Кунжутик, и сегодня у нас {dish_name}. Посмотрите на эту подачу: {plating}.",
                duration_sec=12,
                raw_response={"provider": self.provider_name, "mode": "mock"},
            )
        if platform == "vk":
            return GeneratedContent(
                platform=platform,
                kind=kind,
                hook=f"{dish_name} в сторис",
                caption="Кунжутик на связи: тут настолько вкусный кадр, что телефон сам хочет откусить уголок.",
                cta="Пишите, кому бы вы это отправили прямо сейчас.",
                hashtags=["#кунжутик", "#еда"],
                voice_script=f"Кунжутик показывает {dish_name}. И да, это тот случай, когда сторис пахнет вкусно.",
                duration_sec=10,
                raw_response={"provider": self.provider_name, "mode": "mock"},
            )
        return GeneratedContent(
            platform=platform,
            kind=kind,
            hook=f"Новость про {dish_name}",
            caption=f"Кунжутик рекомендует обратить внимание на {dish_name}: свежая подача и понятный аппетитный акцент.",
            cta="Сохраните место и загляните на дегустацию.",
            hashtags=[],
            voice_script="",
            duration_sec=0,
            raw_response={
                "provider": self.provider_name,
                "mode": "mock",
                "long_text": f"{dish_name} с нотами {ingredient_line}. Визуально: {mood}. Формат подачи: {plating}.",
            },
        )
