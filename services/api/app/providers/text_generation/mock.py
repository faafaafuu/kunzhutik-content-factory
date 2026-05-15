from __future__ import annotations

from app.models.character_profile import CharacterProfile
from app.providers.text_generation.base import TextGenerationProvider
from app.providers.text_generation.schemas import GeneratedContent
from app.providers.vision.schemas import VisionAnalysisResult


class MockTextGenerationProvider(TextGenerationProvider):
    provider_name = "mock-text-v1"

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
