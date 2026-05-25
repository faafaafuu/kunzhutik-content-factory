from __future__ import annotations

import subprocess
import tempfile
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.ai_video_scene import AIVideoScene
from app.models.content_draft import ContentDraft
from app.models.media_asset import MediaAsset
from app.models.project import Project
from app.models.scene_plan import ScenePlan
from app.models.upload import Upload
from app.models.video_asset import VideoAsset
from app.models.voice_asset import VoiceAsset
from app.providers.ai_video.factory import get_ai_video_provider
from app.providers.video_render.ffmpeg_fallback import VIDEO_HEIGHT, VIDEO_WIDTH
from app.services.audit import log_event
from app.services.media_generation import _create_media_asset, _write_render_output
from app.services.storage import download_bytes
from shared.enums import AssetKind, PipelineStatus

CHARACTER_PROMPT = (
    "Keep the same character identity in every scene: a small sesame seed mascot named Kunzhutik wearing a blue apron, "
    "expressive friendly eyes, soft 3D animation style, warm food commercial mood. Do not change the character's body "
    "shape, color, outfit, or face."
)

STYLE_PROMPT = (
    "Добрый 3D food/cartoon reels, вертикальный кадр 9:16, мягкий свет, аппетитные текстуры еды, "
    "живой маленький маскот Кунжутик в синем фартуке, дружелюбная реклама без детскости и без крипоты."
)


def create_scene_plan(
    db: Session,
    upload_id: UUID,
    *,
    content_draft_id: UUID | None = None,
    total_duration_sec: int | None = None,
    aspect_ratio: str | None = None,
    scenes_count: int | None = None,
    style_reference: str | None = None,
    actor: str,
) -> ScenePlan:
    upload = _get_upload(db, upload_id)
    draft = _get_draft(db, upload_id, content_draft_id)
    duration = total_duration_sec or settings.ai_video_default_duration_sec * (scenes_count or settings.ai_video_scenes_count)
    count = scenes_count or settings.ai_video_scenes_count
    plan_scenes = _build_mock_scene_plan(draft, duration, count)
    plan = ScenePlan(
        project_id=upload.project_id,
        upload_id=upload.id,
        content_draft_id=draft.id,
        status="draft",
        total_duration_sec=Decimal(str(duration)),
        aspect_ratio=aspect_ratio or settings.ai_video_default_aspect_ratio,
        style_prompt=style_reference or STYLE_PROMPT,
        character_prompt=CHARACTER_PROMPT,
        scenes_json=plan_scenes,
        metadata_json={"provider": "mock-scene-planner-v1", "video_mode": "ai_video"},
    )
    db.add(plan)
    db.flush()
    _sync_scene_rows(db, plan)
    log_event(db, upload.project_id, "upload", str(upload.id), "scene_plan.created", actor, {"scene_plan_id": str(plan.id), "scene_count": len(plan_scenes)})
    db.commit()
    db.refresh(plan)
    return plan


def list_scene_plans(db: Session, upload_id: UUID) -> list[ScenePlan]:
    return db.query(ScenePlan).filter(ScenePlan.upload_id == upload_id).order_by(ScenePlan.created_at.desc()).all()


def get_scene_plan_or_404(db: Session, scene_plan_id: UUID) -> ScenePlan:
    plan = db.query(ScenePlan).filter(ScenePlan.id == scene_plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Scene plan not found")
    return plan


def list_scenes(db: Session, scene_plan_id: UUID) -> list[AIVideoScene]:
    return db.query(AIVideoScene).filter(AIVideoScene.scene_plan_id == scene_plan_id).order_by(AIVideoScene.scene_number.asc()).all()


def regenerate_scene_plan(db: Session, scene_plan_id: UUID, *, actor: str, reason: str | None = None, scenes_count: int | None = None) -> ScenePlan:
    plan = get_scene_plan_or_404(db, scene_plan_id)
    draft = db.query(ContentDraft).filter(ContentDraft.id == plan.content_draft_id).first()
    if not draft:
        raise HTTPException(status_code=409, detail="Scene plan draft not found")
    count = scenes_count or len(plan.scenes_json or []) or settings.ai_video_scenes_count
    plan.scenes_json = _build_mock_scene_plan(draft, int(plan.total_duration_sec), count)
    plan.status = "draft"
    plan.metadata_json = {**(plan.metadata_json or {}), "regenerate_reason": reason, "provider": "mock-scene-planner-v1"}
    db.query(AIVideoScene).filter(AIVideoScene.scene_plan_id == plan.id).delete()
    db.flush()
    _sync_scene_rows(db, plan)
    log_event(db, plan.project_id, "upload", str(plan.upload_id), "scene_plan.regenerated", actor, {"scene_plan_id": str(plan.id), "reason": reason})
    db.commit()
    db.refresh(plan)
    return plan


def generate_scenes(db: Session, scene_plan_id: UUID, *, actor: str) -> ScenePlan:
    plan = get_scene_plan_or_404(db, scene_plan_id)
    upload = _get_upload(db, plan.upload_id)
    _attach_project(db, upload)
    provider = get_ai_video_provider()
    plan.status = "generating"
    db.flush()
    draft = db.query(ContentDraft).filter(ContentDraft.id == plan.content_draft_id).first()
    if not draft:
        raise HTTPException(status_code=409, detail="Scene plan draft not found")
    for scene in list_scenes(db, plan.id):
        _generate_single_scene(db, plan=plan, scene=scene, upload=upload, draft=draft, provider=provider)
    statuses = {scene.status for scene in list_scenes(db, plan.id)}
    plan.status = "ready_for_render" if statuses == {"generated"} else "partially_generated" if "generated" in statuses else "failed"
    log_event(db, plan.project_id, "upload", str(plan.upload_id), "ai_video_scenes.generated", actor, {"scene_plan_id": str(plan.id), "status": plan.status})
    db.commit()
    db.refresh(plan)
    return plan


def regenerate_scene(db: Session, scene_id: UUID, *, actor: str, reason: str | None = None) -> AIVideoScene:
    scene = db.query(AIVideoScene).filter(AIVideoScene.id == scene_id).first()
    if not scene:
        raise HTTPException(status_code=404, detail="AI video scene not found")
    plan = get_scene_plan_or_404(db, scene.scene_plan_id)
    upload = _get_upload(db, plan.upload_id)
    _attach_project(db, upload)
    draft = db.query(ContentDraft).filter(ContentDraft.id == plan.content_draft_id).first()
    if not draft:
        raise HTTPException(status_code=409, detail="Scene plan draft not found")
    _generate_single_scene(db, plan=plan, scene=scene, upload=upload, draft=draft, provider=get_ai_video_provider())
    statuses = {row.status for row in list_scenes(db, plan.id)}
    plan.status = "ready_for_render" if statuses == {"generated"} else "partially_generated" if "generated" in statuses else "failed"
    log_event(db, scene.project_id, "upload", str(scene.upload_id), "ai_video_scene.regenerated", actor, {"scene_id": str(scene_id), "reason": reason})
    db.commit()
    db.refresh(scene)
    return scene


def render_final_video(db: Session, scene_plan_id: UUID, *, actor: str) -> VideoAsset:
    plan = get_scene_plan_or_404(db, scene_plan_id)
    upload = _get_upload(db, plan.upload_id)
    _attach_project(db, upload)
    draft = db.query(ContentDraft).filter(ContentDraft.id == plan.content_draft_id).first()
    if not draft:
        raise HTTPException(status_code=409, detail="Scene plan draft not found")
    scenes = [scene for scene in list_scenes(db, plan.id) if scene.status == "generated" and scene.asset_id]
    if not scenes:
        raise HTTPException(status_code=409, detail="No generated scenes to render")
    plan.status = "rendering"
    db.flush()
    with tempfile.TemporaryDirectory(prefix="kunzhutik-ai-final-") as tmp_dir_name:
        tmp_dir = Path(tmp_dir_name)
        concat_file = tmp_dir / "concat.txt"
        scene_paths = []
        for scene in scenes:
            asset = db.query(MediaAsset).filter(MediaAsset.id == scene.asset_id).first()
            scene_path = tmp_dir / f"scene-{scene.scene_number}.mp4"
            scene_path.write_bytes(download_bytes(asset.storage_key))
            scene_paths.append(scene_path)
        concat_file.write_text("\n".join(f"file '{path}'" for path in scene_paths), encoding="utf-8")
        video_path = tmp_dir / "final.mp4"
        _concat_scenes(concat_file, video_path)
        preview_path = tmp_dir / "preview.jpg"
        _render_preview(video_path, preview_path)
        duration = sum((scene.duration_sec for scene in scenes), Decimal("0"))
        video_media = _create_media_asset(db, upload, draft, AssetKind.video, video_path, "ai-final-video.mp4", "video/mp4", VIDEO_WIDTH, VIDEO_HEIGHT, duration, {"provider": "ai-video-final-render", "scene_plan_id": str(plan.id)})
        preview_media = _create_media_asset(db, upload, draft, AssetKind.preview, preview_path, "ai-final-preview.jpg", "image/jpeg", VIDEO_WIDTH, VIDEO_HEIGHT, metadata={"provider": "ai-video-final-render", "scene_plan_id": str(plan.id)})
    video_asset = VideoAsset(project_id=plan.project_id, content_draft_id=plan.content_draft_id, status=PipelineStatus.completed, template_name="ai_video_scene_sequence_v1", aspect_ratio=plan.aspect_ratio, asset_id=video_media.id, preview_asset_id=preview_media.id)
    db.add(video_asset)
    plan.status = "ready_for_review"
    db.flush()
    log_event(db, plan.project_id, "upload", str(plan.upload_id), "ai_video_final.rendered", actor, {"scene_plan_id": str(plan.id), "video_asset_id": str(video_asset.id)})
    db.commit()
    db.refresh(video_asset)
    return video_asset


def _sync_scene_rows(db: Session, plan: ScenePlan) -> None:
    for scene_payload in plan.scenes_json:
        db.add(AIVideoScene(project_id=plan.project_id, upload_id=plan.upload_id, scene_plan_id=plan.id, content_draft_id=plan.content_draft_id, scene_number=scene_payload["scene_number"], status=scene_payload.get("status", "queued"), provider="mock", duration_sec=Decimal(str(scene_payload["duration_sec"])), visual_prompt=scene_payload["visual_prompt"], voice_text=scene_payload.get("voice_text"), subtitle_text=scene_payload.get("subtitle_text"), camera=scene_payload.get("camera"), emotion=scene_payload.get("emotion"), raw_response={}))
    db.flush()


def _generate_single_scene(db: Session, *, plan: ScenePlan, scene: AIVideoScene, upload: Upload, draft: ContentDraft, provider) -> None:
    scene.status = "generating"
    db.flush()
    try:
        result = provider.generate_scene(
            prompt=f"{plan.character_prompt}\n\n{scene.visual_prompt}",
            image_reference_url=None,
            character_reference_url=None,
            duration_sec=float(scene.duration_sec),
            aspect_ratio=plan.aspect_ratio,
            context={"scene_number": scene.scene_number, "subtitle_text": scene.subtitle_text},
        )
        scene_file = _write_render_output(result.video_bytes, result.video_url, Path(tempfile.mkdtemp(prefix="kunzhutik-scene-save-")) / f"scene-{scene.scene_number}.mp4")
        media = _create_media_asset(
            db=db,
            upload=upload,
            draft=draft,
            kind=AssetKind.video,
            file_path=scene_file,
            file_name=f"ai-scene-{scene.scene_number}.mp4",
            mime_type="video/mp4",
            width=VIDEO_WIDTH,
            height=VIDEO_HEIGHT,
            duration_seconds=Decimal(str(result.duration_sec)).quantize(Decimal("0.01")),
            metadata={"provider": result.provider, "scene_plan_id": str(plan.id), "scene_number": scene.scene_number, **result.raw_response},
        )
        scene.status = "generated"
        scene.provider = result.provider
        scene.provider_scene_id = result.scene_id
        scene.asset_id = media.id
        scene.raw_response = result.raw_response
        scene.error_message = result.error_message
    except Exception as exc:
        scene.status = "failed"
        scene.error_message = str(exc)


def _build_mock_scene_plan(draft: ContentDraft, total_duration_sec: int, scenes_count: int) -> list[dict]:
    base_duration = max(3, round(total_duration_sec / scenes_count))
    story = [
        ("Хук", "Кунжутик замечает блюдо, оживляется и делает дружелюбный жест к камере.", "wide push-in", "curious"),
        ("Эмоция", "Кунжутик радостно реагирует на аромат, рядом появляются пар и аппетитные детали.", "medium orbit", "delighted"),
        ("Показ блюда", "Крупный план текстуры блюда, соус, свежесть, хруст, Кунжутик показывает детали.", "macro food shot", "proud"),
        ("CTA", "Кунжутик приглашает попробовать блюдо сегодня, финальный брендовый кадр.", "front hero shot", "friendly"),
    ]
    scenes = []
    for index in range(scenes_count):
        title, visual, camera, emotion = story[index % len(story)]
        subtitle = draft.cta if index == scenes_count - 1 and draft.cta else (draft.title or draft.caption)[:90]
        scenes.append({"scene_number": index + 1, "duration_sec": base_duration, "visual_prompt": f"{title}: {visual} Стиль: {STYLE_PROMPT}", "voice_text": (draft.script_text or draft.caption)[:240], "subtitle_text": subtitle, "camera": camera, "emotion": emotion, "status": "queued"})
    return scenes


def _get_upload(db: Session, upload_id: UUID) -> Upload:
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    return upload


def _get_draft(db: Session, upload_id: UUID, content_draft_id: UUID | None) -> ContentDraft:
    query = db.query(ContentDraft).filter(ContentDraft.upload_id == upload_id)
    if content_draft_id:
        query = query.filter(ContentDraft.id == content_draft_id)
    draft = query.order_by(ContentDraft.created_at.asc()).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Content draft not found")
    return draft


def _attach_project(db: Session, upload: Upload) -> None:
    upload.project = db.query(Project).filter(Project.id == upload.project_id).first()


def _concat_scenes(concat_file: Path, output_path: Path) -> None:
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(output_path)], check=True, capture_output=True, text=True, timeout=60)


def _render_preview(video_path: Path, preview_path: Path) -> None:
    subprocess.run(["ffmpeg", "-y", "-i", str(video_path), "-frames:v", "1", str(preview_path)], check=True, capture_output=True, text=True, timeout=20)
