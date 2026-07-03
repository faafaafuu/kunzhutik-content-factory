from uuid import UUID

from app.core.celery_app import celery_app


def enqueue_upload_pipeline(upload_id: UUID) -> None:
    celery_app.send_task("app.tasks.process_upload_pipeline", kwargs={"upload_id": str(upload_id)})


def enqueue_approval_dispatch(approval_task_id: UUID) -> None:
    celery_app.send_task("app.tasks.dispatch_approval_preview", kwargs={"approval_task_id": str(approval_task_id)})


def enqueue_video_stage(upload_id: UUID, scene_plan_id: UUID) -> None:
    celery_app.send_task("app.tasks.produce_video_stage", kwargs={"upload_id": str(upload_id), "scene_plan_id": str(scene_plan_id)})


def enqueue_publication_task(publication_task_id: UUID) -> None:
    celery_app.send_task("app.tasks.publish_publication_task", kwargs={"publication_task_id": str(publication_task_id)})
