from sqlalchemy.orm import Session

from app.models.character_profile import CharacterProfile
from app.models.project import Project


DEFAULT_APPEARANCE = "Кунжутное зёрнышко в синем фартуке."
DEFAULT_TONE = "Дружелюбный, с юмором, заботливый."
DEFAULT_VOICE_STYLE = "Приятный, энергичный, живой, без кринжа и без детскости."


def build_persona_prompt(name: str) -> str:
    return (
        f"Ты персонаж {name}. Пиши только на русском. "
        "Твой голос дружелюбный, тёплый, с лёгким юмором. "
        "Не скатывайся в детскость, клоунаду или кринж. "
        "Подавай еду аппетитно, живо и с заботой о госте."
    )


def create_default_character(db: Session, project: Project, name: str) -> CharacterProfile:
    character = CharacterProfile(
        project_id=project.id,
        name=name,
        appearance=DEFAULT_APPEARANCE,
        tone=DEFAULT_TONE,
        language="ru",
        voice_style=DEFAULT_VOICE_STYLE,
        persona_prompt=build_persona_prompt(name),
        is_default=True,
    )
    db.add(character)
    db.flush()
    return character

