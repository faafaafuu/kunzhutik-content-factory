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
from app.services.content_generation import build_persona_drafts
from app.services.generation_readiness import validate_generation_providers_ready
from app.services.media_generation import generate_media_assets_for_drafts
from app.services.publications import publish_task_with_provider
from app.services.scene_plans import plan_ai_video_for_upload, produce_ai_video_for_plan
from app.services.vision_analysis import analyze_upload_with_configured_provider
from shared.enums import ApprovalStatus, PipelineStatus

logger = get_task_logger(__name__)


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
        validate_generation_providers_ready()

        analysis_payload = analyze_upload_with_configured_provider(upload).model_payload()
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
        for payload in build_persona_drafts(character, analysis):
            draft = ContentDraft(
                project_id=upload.project_id,
                upload_id=upload.id,
                analysis_result_id=analysis.id,
                persona_name=persona_name,
                status=PipelineStatus.completed,
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

        video_mode = settings.video_mode.lower().strip()
        drafts_preview = [
            {
                "platform": draft.platform.value,
                "kind": draft.kind.value,
                "caption": draft.caption,
                "cta": draft.cta,
                "script_text": draft.script_text,
            }
            for draft in drafts
        ]
        shared_story = bool(drafts and (drafts[0].metadata_json or {}).get("shared_story"))
        story_preview = None
        if shared_story:
            story_preview = {
                "hook": drafts[0].title,
                "caption": drafts[0].caption,
                "cta": drafts[0].cta,
                "voice_script": drafts[0].script_text,
                "platforms": [draft.platform.value for draft in drafts],
            }
        if video_mode == "ai_video":
            scene_plan = plan_ai_video_for_upload(db, upload, drafts)
            stage = "content"
            creative_payload = {"video_mode": "ai_video", "scene_plan_id": str(scene_plan.id), "draft_count": len(drafts), "stage": stage}
            preview_payload = {
                "dish_name": analysis.dish_name,
                "analysis_provider": analysis.provider,
                "drafts": drafts_preview,
                "story": story_preview,
                "scene_plan_id": str(scene_plan.id),
                "scenes": scene_plan.scenes_json,
                "scene_plan_provider": (scene_plan.metadata_json or {}).get("provider"),
                "mock": analysis.provider.startswith("mock"),
                "video_mode": video_mode,
                "stage": stage,
            }
            event_name = "scenario.ready_for_review"
        elif video_mode == "template":
            generate_media_assets_for_drafts(db, upload, drafts)
            stage = "video"
            creative_payload = {"video_mode": "template", "draft_count": len(drafts), "stage": stage}
            preview_payload = {
                "dish_name": analysis.dish_name,
                "analysis_provider": analysis.provider,
                "drafts": drafts_preview,
                "story": story_preview,
                "mock": analysis.provider.startswith("mock"),
                "video_mode": video_mode,
                "video_template": "mascot_story_v1",
                "stage": stage,
            }
            event_name = "creative_render.completed"
        else:
            raise ValueError(f"Unsupported VIDEO_MODE: {settings.video_mode}")
        log_event(
            db,
            upload.project_id,
            "upload",
            str(upload.id),
            event_name,
            "worker",
            creative_payload,
        )

        approval = ApprovalTask(
            project_id=upload.project_id,
            upload_id=upload.id,
            status=ApprovalStatus.pending,
            stage=stage,
            telegram_chat_id=None if settings.telegram_open_access else settings.telegram_approval_chat_id,
            preview_payload=preview_payload,
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
            {"approval_task_id": str(approval.id), "stage": stage},
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


@celery_app.task(name="app.tasks.produce_video_stage", autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def produce_video_stage(upload_id: str, scene_plan_id: str) -> None:
    """Stage 2 of the pipeline: runs after the scenario is approved — the only paid step."""
    db: Session = SessionLocal()
    try:
        upload = db.query(Upload).filter(Upload.id == UUID(upload_id)).first()
        if not upload:
            raise ValueError(f"Upload {upload_id} not found")

        upload.status = PipelineStatus.processing
        log_event(db, upload.project_id, "upload", str(upload.id), "video_stage.started", "worker", {"scene_plan_id": scene_plan_id})
        db.commit()

        plan = produce_ai_video_for_plan(db, UUID(scene_plan_id))

        analysis = (
            db.query(AnalysisResult)
            .filter(AnalysisResult.upload_id == upload.id)
            .order_by(AnalysisResult.created_at.desc())
            .first()
        )
        draft = db.query(ContentDraft).filter(ContentDraft.id == plan.content_draft_id).first()
        metadata = plan.metadata_json or {}
        approval = ApprovalTask(
            project_id=upload.project_id,
            upload_id=upload.id,
            status=ApprovalStatus.pending,
            stage="video",
            telegram_chat_id=None if settings.telegram_open_access else settings.telegram_approval_chat_id,
            preview_payload={
                "dish_name": analysis.dish_name if analysis else None,
                "scene_plan_id": str(plan.id),
                "final_video_media_id": metadata.get("final_video_media_id"),
                "final_preview_media_id": metadata.get("final_preview_media_id"),
                "caption": draft.caption if draft else None,
                "cta": draft.cta if draft else None,
                "video_mode": "ai_video",
                "stage": "video",
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
            {"approval_task_id": str(approval.id), "stage": "video"},
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


@celery_app.task(name="app.tasks.publish_publication_task", autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def publish_publication_task(publication_task_id: str) -> None:
    db: Session = SessionLocal()
    try:
        publish_task_with_provider(db, UUID(publication_task_id))
    finally:
        db.close()


def _format_approval_message(payload: dict) -> str:
    stage = payload.get("stage", "video")
    lines: list[str] = []
    if stage == "content":
        lines.append("Кунжутик принёс сценарий на согласование (видео ещё не генерировалось).")
        lines.append(f"Блюдо: {payload.get('dish_name', 'без названия')}")
        lines.append("")
        story = payload.get("story")
        if story:
            platforms = ", ".join(story.get("platforms") or [])
            lines.append(f"Публикация (одна на все площадки: {platforms}):")
            lines.append(story.get("caption") or "")
            if story.get("cta"):
                lines.append(f"CTA: {story['cta']}")
            lines.append("")
        else:
            for draft in payload.get("drafts", []):
                lines.append(f"[{draft['platform']}/{draft['kind']}] {draft['caption']}")
                if draft.get("cta"):
                    lines.append(f"CTA: {draft['cta']}")
                lines.append("")
        scenes = payload.get("scenes") or []
        if scenes:
            lines.append("Сценарий ролика:")
            for scene in scenes:
                lines.append(f"{scene.get('scene_number')}. {scene.get('subtitle_text') or scene.get('voice_text') or ''} ({scene.get('duration_sec')}с)")
            lines.append("")
        lines.append("После одобрения запустится платная генерация видео.")
    else:
        lines.append("Кунжутик принёс готовый ролик на согласование.")
        lines.append(f"Блюдо: {payload.get('dish_name', 'без названия')}")
        if payload.get("caption"):
            lines.append("")
            lines.append(payload["caption"])
        if payload.get("cta"):
            lines.append(f"CTA: {payload['cta']}")
        lines.append("")
        lines.append("После одобрения контент уйдёт в публикацию.")
    return "\n".join(lines)


async def _send_telegram_message(token: str, chat_id: str, text: str, keyboard: InlineKeyboardMarkup):
    bot = Bot(token=token)
    try:
        return await bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
    finally:
        await bot.session.close()
