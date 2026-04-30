from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import UUID

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from celery.utils.log import get_task_logger
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.analysis_result import AnalysisResult
from app.models.approval_task import ApprovalTask
from app.models.character_profile import CharacterProfile
from app.models.content_draft import ContentDraft
from app.models.upload import Upload
from app.services.audit import log_event
from app.services.media_generation import generate_media_assets_for_drafts
from shared.enums import ApprovalStatus, ContentPlatform, DraftKind, PipelineStatus

logger = get_task_logger(__name__)


def build_mock_analysis(upload: Upload) -> dict:
    return {
        "provider": "mock-vision-v1",
        "dish_name": "Авторское блюдо дня",
        "ingredients": ["кунжут", "соус", "свежая зелень"],
        "visual_mood": "аппетитный и тёплый",
        "plating_style": "аккуратная ресторанная подача",
        "features_json": {
            "lighting": "soft warm",
            "camera_angle": "close-up",
            "hero_element": "texture",
        },
        "raw_payload": {
            "note": "Stage 1 mock analysis. Replace with real vision adapter in Stage 2."
        },
    }


def build_persona_drafts(persona_name: str, analysis: AnalysisResult) -> list[dict]:
    dish_name = analysis.dish_name or "наше блюдо"
    mood = analysis.visual_mood or "аппетитное настроение"
    plating = analysis.plating_style or "красивая подача"
    ingredient_line = ", ".join(analysis.ingredients[:3]) if analysis.ingredients else "секретные вкусности"
    return [
        {
            "platform": ContentPlatform.instagram,
            "kind": DraftKind.post,
            "title": f"{dish_name} от Кунжутика",
            "caption": f"Я, Кунжутик, уже тут и шепчу: {dish_name} выглядит так, будто тарелка решила устроить праздник вкуса.",
            "cta": "Заглядывайте в гости и пробуйте, пока я не съел взглядом всё сам.",
            "short_text": f"{dish_name}. {mood}.",
            "long_text": f"{dish_name} с акцентами {ingredient_line}. В кадре {mood}, а на тарелке {plating}.",
            "script_text": f"Я Кунжутик, и сегодня у нас {dish_name}. Посмотрите на эту подачу: {plating}.",
        },
        {
            "platform": ContentPlatform.vk,
            "kind": DraftKind.story,
            "title": f"{dish_name} в сторис",
            "caption": f"Кунжутик на связи: тут настолько вкусный кадр, что телефон сам хочет откусить уголок.",
            "cta": "Пишите, кому бы вы это отправили прямо сейчас.",
            "short_text": f"{dish_name}. {ingredient_line}.",
            "long_text": f"Сегодняшний герой ленты: {dish_name}. Состав намекает на {ingredient_line}, а настроение кадра {mood}.",
            "script_text": f"Кунжутик показывает {dish_name}. И да, это тот случай, когда сторис пахнет вкусно.",
        },
        {
            "platform": ContentPlatform.yandex_maps,
            "kind": DraftKind.news,
            "title": f"Новость про {dish_name}",
            "caption": f"Кунжутик рекомендует обратить внимание на {dish_name}: свежая подача и понятный аппетитный акцент.",
            "cta": "Сохраните место и загляните на дегустацию.",
            "short_text": f"{dish_name} уже ждёт гостей.",
            "long_text": f"{dish_name} с нотами {ingredient_line}. Визуально: {mood}. Формат подачи: {plating}.",
            "script_text": None,
        },
    ]


@celery_app.task(name="app.tasks.process_upload_pipeline", autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def process_upload_pipeline(upload_id: str) -> None:
    db: Session = SessionLocal()
    try:
        upload = db.query(Upload).filter(Upload.id == UUID(upload_id)).first()
        if not upload:
            raise ValueError(f"Upload {upload_id} not found")

        upload.status = PipelineStatus.processing
        log_event(db, upload.project_id, "upload", str(upload.id), "pipeline.started", "worker", {})
        db.flush()

        analysis_payload = build_mock_analysis(upload)
        analysis = AnalysisResult(
            project_id=upload.project_id,
            upload_id=upload.id,
            status=PipelineStatus.completed,
            **analysis_payload,
        )
        db.add(analysis)
        db.flush()
        log_event(
            db,
            upload.project_id,
            "upload",
            str(upload.id),
            "analysis.completed",
            "worker",
            {"analysis_result_id": str(analysis.id), "provider": analysis.provider},
        )

        character = (
            db.query(CharacterProfile)
            .filter(CharacterProfile.project_id == upload.project_id, CharacterProfile.is_default.is_(True))
            .first()
        )
        persona_name = character.name if character else "Кунжутик"

        drafts: list[ContentDraft] = []
        for payload in build_persona_drafts(persona_name, analysis):
            draft = ContentDraft(
                project_id=upload.project_id,
                upload_id=upload.id,
                analysis_result_id=analysis.id,
                persona_name=persona_name,
                status=PipelineStatus.completed,
                metadata_json={"generation_mode": "stage1_mock"},
                **payload,
            )
            db.add(draft)
            drafts.append(draft)
        db.flush()
        log_event(
            db,
            upload.project_id,
            "upload",
            str(upload.id),
            "content_drafts.completed",
            "worker",
            {"draft_count": len(drafts)},
        )

        generate_media_assets_for_drafts(db, upload, drafts)
        log_event(
            db,
            upload.project_id,
            "upload",
            str(upload.id),
            "creative_render.completed",
            "worker",
            {"draft_count": len(drafts)},
        )

        approval = ApprovalTask(
            project_id=upload.project_id,
            upload_id=upload.id,
            status=ApprovalStatus.pending,
            telegram_chat_id=None if settings.telegram_open_access else settings.telegram_approval_chat_id,
            preview_payload={
                "dish_name": analysis.dish_name,
                "drafts": [
                    {
                        "platform": draft.platform.value,
                        "kind": draft.kind.value,
                        "caption": draft.caption,
                        "cta": draft.cta,
                        "script_text": draft.script_text,
                    }
                    for draft in drafts
                ],
                "mock": True,
                "video_template": "mascot_story_v1",
            },
        )
        db.add(approval)
        upload.status = PipelineStatus.needs_review
        db.flush()
        log_event(
            db,
            upload.project_id,
            "upload",
            str(upload.id),
            "approval.created",
            "worker",
            {"approval_task_id": str(approval.id)},
        )
        db.commit()

        if settings.telegram_bot_token and settings.telegram_approval_chat_id and not settings.telegram_open_access:
            dispatch_approval_preview.delay(str(approval.id))
    except Exception:
        db.rollback()
        upload = db.query(Upload).filter(Upload.id == UUID(upload_id)).first()
        if upload:
            upload.status = PipelineStatus.failed
            db.commit()
        raise
    finally:
        db.close()


@celery_app.task(name="app.tasks.dispatch_approval_preview", autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def dispatch_approval_preview(approval_task_id: str) -> None:
    db: Session = SessionLocal()
    try:
        approval = db.query(ApprovalTask).filter(ApprovalTask.id == UUID(approval_task_id)).first()
        if not approval:
            raise ValueError(f"ApprovalTask {approval_task_id} not found")
        if settings.telegram_open_access and not approval.telegram_chat_id:
            logger.info("Telegram open access is enabled; skipping direct dispatch for %s", approval_task_id)
            return
        if not settings.telegram_bot_token or not approval.telegram_chat_id:
            logger.info("Telegram is not configured; skipping approval dispatch for %s", approval_task_id)
            return

        message_text = _format_approval_message(approval.preview_payload)
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="Approve", callback_data=f"approve:{approval.id}"),
                    InlineKeyboardButton(text="Reject", callback_data=f"reject:{approval.id}"),
                    InlineKeyboardButton(text="Regenerate", callback_data=f"regenerate:{approval.id}"),
                ]
            ]
        )
        message = asyncio.run(_send_telegram_message(settings.telegram_bot_token, approval.telegram_chat_id, message_text, keyboard))
        approval.status = ApprovalStatus.dispatched
        approval.telegram_message_id = str(message.message_id)
        approval.dispatched_at = datetime.now(timezone.utc)
        log_event(
            db,
            approval.project_id,
            "upload",
            str(approval.upload_id),
            "approval.dispatched",
            "worker",
            {"approval_task_id": str(approval.id), "telegram_message_id": approval.telegram_message_id},
        )
        db.commit()
    finally:
        db.close()


def _format_approval_message(payload: dict) -> str:
    drafts = payload.get("drafts", [])
    lines = [
        "Кунжутик принёс контент на согласование.",
        f"Блюдо: {payload.get('dish_name', 'без названия')}",
        "",
    ]
    for draft in drafts:
        lines.append(f"[{draft['platform']}/{draft['kind']}] {draft['caption']}")
        if draft.get("cta"):
            lines.append(f"CTA: {draft['cta']}")
        lines.append("")
    lines.append("Решение можно принять в API или через Telegram callback skeleton.")
    return "\n".join(lines)


async def _send_telegram_message(token: str, chat_id: str, text: str, keyboard: InlineKeyboardMarkup):
    bot = Bot(token=token)
    try:
        return await bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
    finally:
        await bot.session.close()
