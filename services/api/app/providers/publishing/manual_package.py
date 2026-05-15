from __future__ import annotations

import re
from io import BytesIO
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from app.models.content_draft import ContentDraft
from app.models.media_asset import MediaAsset
from app.models.publication_task import PublicationTask
from app.services.storage import download_bytes, get_public_asset_url, upload_bytes


def build_manual_package(
    task: PublicationTask,
    assets: list[MediaAsset],
    draft: ContentDraft,
    *,
    platform_label: str,
) -> dict:
    package_id = f"manual-{task.platform.value}-{uuid4().hex[:12]}"
    package_key = f"projects/{task.project_id}/publication-packages/{task.id}/{package_id}.zip"
    manifest_assets = []

    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("caption.txt", _caption_text(draft))
        archive.writestr("hashtags.txt", "\n".join((draft.metadata_json or {}).get("hashtags", [])))
        archive.writestr("instructions.md", _instructions(task, draft, platform_label))

        for index, asset in enumerate(assets, start=1):
            filename = f"assets/{index:02d}-{_safe_filename(asset.file_name)}"
            try:
                archive.writestr(filename, download_bytes(asset.storage_key))
                manifest_assets.append(
                    {
                        "file": filename,
                        "media_asset_id": str(asset.id),
                        "kind": asset.kind.value,
                        "mime_type": asset.mime_type,
                        "storage_key": asset.storage_key,
                    }
                )
            except Exception as exc:
                manifest_assets.append(
                    {
                        "media_asset_id": str(asset.id),
                        "kind": asset.kind.value,
                        "mime_type": asset.mime_type,
                        "storage_key": asset.storage_key,
                        "error": str(exc),
                    }
                )

        archive.writestr(
            "manifest.json",
            _json_dump(
                {
                    "package_id": package_id,
                    "platform": task.platform.value,
                    "content_draft_id": str(draft.id),
                    "publication_task_id": str(task.id),
                    "assets": manifest_assets,
                }
            ),
        )

    upload_bytes(package_key, buffer.getvalue(), "application/zip")
    return {
        "package_id": package_id,
        "package_storage_key": package_key,
        "package_url": get_public_asset_url(package_key),
        "mode": "manual_package",
        "asset_count": len(manifest_assets),
    }


def _caption_text(draft: ContentDraft) -> str:
    parts = [draft.caption.strip()]
    if draft.cta:
        parts.append(draft.cta.strip())
    hashtags = (draft.metadata_json or {}).get("hashtags", [])
    if hashtags:
        parts.append(" ".join(hashtags))
    return "\n\n".join(part for part in parts if part)


def _instructions(task: PublicationTask, draft: ContentDraft, platform_label: str) -> str:
    return "\n".join(
        [
            f"# Manual publishing package: {platform_label}",
            "",
            f"- Publication task: `{task.id}`",
            f"- Platform: `{task.platform.value}`",
            f"- Draft: `{draft.id}` v{draft.version}",
            "",
            "1. Open the target platform admin interface.",
            "2. Upload the media files from `assets/`.",
            "3. Paste `caption.txt` as the post text.",
            "4. Use `hashtags.txt` if the platform supports hashtags.",
            "5. After publication, paste the remote URL back into operations/audit notes if needed.",
        ]
    )


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    return cleaned[:120] or "asset.bin"


def _json_dump(value: dict) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
