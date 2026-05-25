from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_operator
from app.models.operator_user import OperatorUser
from app.schemas.scene_plan import (
    AIVideoSceneRead,
    FinalVideoRenderResponse,
    SceneGenerationResponse,
    ScenePlanCreateRequest,
    ScenePlanDetail,
    ScenePlanListResponse,
    ScenePlanRegenerateRequest,
    SceneRegenerateRequest,
)
from app.services.scene_plans import (
    create_scene_plan,
    generate_scenes,
    get_scene_plan_or_404,
    list_scene_plans,
    list_scenes,
    regenerate_scene,
    regenerate_scene_plan,
    render_final_video,
)

router = APIRouter(tags=["scene-plans"])


@router.post("/uploads/{upload_id}/scene-plans", response_model=ScenePlanDetail)
def create_for_upload(
    upload_id: UUID,
    payload: ScenePlanCreateRequest,
    db: Session = Depends(get_db),
    user: OperatorUser = Depends(require_operator),
) -> ScenePlanDetail:
    plan = create_scene_plan(
        db,
        upload_id,
        content_draft_id=payload.content_draft_id,
        total_duration_sec=payload.total_duration_sec,
        aspect_ratio=payload.aspect_ratio,
        scenes_count=payload.scenes_count,
        style_reference=payload.style_reference,
        actor=f"dashboard:{user.username}",
    )
    return _detail(db, plan.id)


@router.get("/uploads/{upload_id}/scene-plans", response_model=ScenePlanListResponse)
def list_for_upload(upload_id: UUID, db: Session = Depends(get_db), user: OperatorUser = Depends(require_operator)) -> ScenePlanListResponse:
    return ScenePlanListResponse(scene_plans=[_detail(db, plan.id) for plan in list_scene_plans(db, upload_id)])


@router.get("/scene-plans/{scene_plan_id}", response_model=ScenePlanDetail)
def get_scene_plan(scene_plan_id: UUID, db: Session = Depends(get_db), user: OperatorUser = Depends(require_operator)) -> ScenePlanDetail:
    get_scene_plan_or_404(db, scene_plan_id)
    return _detail(db, scene_plan_id)


@router.post("/scene-plans/{scene_plan_id}/regenerate", response_model=ScenePlanDetail)
def regenerate_plan(
    scene_plan_id: UUID,
    payload: ScenePlanRegenerateRequest,
    db: Session = Depends(get_db),
    user: OperatorUser = Depends(require_operator),
) -> ScenePlanDetail:
    plan = regenerate_scene_plan(db, scene_plan_id, actor=f"dashboard:{user.username}", reason=payload.reason, scenes_count=payload.scenes_count)
    return _detail(db, plan.id)


@router.post("/scene-plans/{scene_plan_id}/generate-scenes", response_model=SceneGenerationResponse)
def generate_plan_scenes(scene_plan_id: UUID, db: Session = Depends(get_db), user: OperatorUser = Depends(require_operator)) -> SceneGenerationResponse:
    plan = generate_scenes(db, scene_plan_id, actor=f"dashboard:{user.username}")
    return SceneGenerationResponse(scene_plan=_detail(db, plan.id))


@router.post("/scene-plans/{scene_plan_id}/render-final-video", response_model=FinalVideoRenderResponse)
def render_plan_final_video(scene_plan_id: UUID, db: Session = Depends(get_db), user: OperatorUser = Depends(require_operator)) -> FinalVideoRenderResponse:
    video_asset = render_final_video(db, scene_plan_id, actor=f"dashboard:{user.username}")
    return FinalVideoRenderResponse(
        scene_plan_id=scene_plan_id,
        video_asset_id=video_asset.id,
        media_asset_id=video_asset.asset_id,
        preview_asset_id=video_asset.preview_asset_id,
        status=video_asset.status.value,
    )


@router.post("/scenes/{scene_id}/regenerate", response_model=AIVideoSceneRead)
def regenerate_one_scene(
    scene_id: UUID,
    payload: SceneRegenerateRequest,
    db: Session = Depends(get_db),
    user: OperatorUser = Depends(require_operator),
) -> AIVideoSceneRead:
    scene = regenerate_scene(db, scene_id, actor=f"dashboard:{user.username}", reason=payload.reason)
    return AIVideoSceneRead.model_validate(scene)


def _detail(db: Session, scene_plan_id: UUID) -> ScenePlanDetail:
    plan = get_scene_plan_or_404(db, scene_plan_id)
    return ScenePlanDetail.model_validate(plan).model_copy(update={"scenes": [AIVideoSceneRead.model_validate(scene) for scene in list_scenes(db, scene_plan_id)]})
