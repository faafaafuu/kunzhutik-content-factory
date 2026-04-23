from enum import StrEnum


class PipelineStatus(StrEnum):
    pending = "pending"
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    needs_review = "needs_review"


class ContentPlatform(StrEnum):
    instagram = "instagram"
    vk = "vk"
    yandex_maps = "yandex_maps"


class DraftKind(StrEnum):
    post = "post"
    story = "story"
    reel = "reel"
    clip = "clip"
    news = "news"


class AssetKind(StrEnum):
    source_photo = "source_photo"
    derived_image = "derived_image"
    voice = "voice"
    video = "video"
    preview = "preview"


class ApprovalStatus(StrEnum):
    pending = "pending"
    dispatched = "dispatched"
    approved = "approved"
    rejected = "rejected"
    regenerate_requested = "regenerate_requested"


class ApprovalTrigger(StrEnum):
    telegram = "telegram"
    dashboard = "dashboard"
    system = "system"


class PublicationStatus(StrEnum):
    pending = "pending"
    scheduled = "scheduled"
    publishing = "publishing"
    published = "published"
    failed = "failed"
    cancelled = "cancelled"

