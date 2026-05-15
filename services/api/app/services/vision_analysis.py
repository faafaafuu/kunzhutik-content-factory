from __future__ import annotations

from dataclasses import dataclass

from app.models.upload import Upload
from app.providers.vision.factory import get_vision_provider
from app.services.storage import download_bytes
from shared.enums import AssetKind


@dataclass(frozen=True)
class VisionAnalysisPayload:
    provider: str
    dish_name: str | None
    ingredients: list[str]
    visual_mood: str | None
    plating_style: str | None
    features_json: dict
    raw_payload: dict

    def model_payload(self) -> dict:
        return {
            "provider": self.provider,
            "dish_name": self.dish_name,
            "ingredients": self.ingredients,
            "visual_mood": self.visual_mood,
            "plating_style": self.plating_style,
            "features_json": self.features_json,
            "raw_payload": self.raw_payload,
        }


def analyze_upload_with_configured_provider(upload: Upload) -> VisionAnalysisPayload:
    source_asset = next((asset for asset in upload.media_assets if asset.kind == AssetKind.source_photo), None)
    if not source_asset:
        raise ValueError("Upload has no source photo asset")

    image_bytes = download_bytes(source_asset.storage_key)
    provider = get_vision_provider()
    result = provider.analyze_image(
        image_bytes=image_bytes,
        mime_type=source_asset.mime_type,
        context={
            "upload_id": str(upload.id),
            "project_id": str(upload.project_id),
            "source_asset_id": str(source_asset.id),
            "file_name": source_asset.file_name,
        },
    )
    payload = result.to_analysis_model_payload(result.raw_response.get("provider", provider.provider_name))
    payload["raw_payload"]["source_asset_id"] = str(source_asset.id)
    return VisionAnalysisPayload(**payload)
