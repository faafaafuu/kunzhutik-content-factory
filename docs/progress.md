# Kunzhutik Progress

## Current Status

Working vertical slice is preserved:

`Upload -> MediaAsset -> AnalysisResult -> ContentDraft -> VoiceAsset / VideoAsset -> ApprovalTask -> PublicationTask -> PublicationResult`

Current step: Stage 6 complete, publishing provider architecture.

## Done

- FastAPI backend, Celery worker, PostgreSQL, Redis, MinIO/S3.
- Telegram bot, Telegram storefront, operator dashboard.
- Temporary HTTPS reverse proxy for Telegram WebApp.
- Dashboard auth with `operator/admin` roles.
- Publication task flow with mock publisher.
- Vision provider architecture with mock fallback and OpenRouter implementation.
- Pipeline smoke in `VISION_PROVIDER=mock`: upload reached `needs_review`, provider `mock-vision-v1`, created `3` drafts, `1` approval, `10` assets.
- Text generation provider architecture with mock fallback and OpenRouter implementation.
- Pipeline smoke in `TEXT_PROVIDER=mock`: upload reached `needs_review`, text provider `mock-text-v1`, created `3` drafts, `1` approval, `10` assets.
- ContentDraft `version` already exists in the schema.
- Added regenerate endpoint for a single content draft.
- Regenerate smoke passed: old draft version `1` remained, new draft version `2` was created with `mock-text-v1`.
- TTS provider architecture with espeak fallback, ElevenLabs implementation, and Yandex SpeechKit implementation.
- Added regenerate endpoint for a single voice asset.
- Pipeline smoke in `TTS_PROVIDER=mock`: upload reached `needs_review`, created `3` voice assets and `10` total assets.
- Regenerate voice smoke passed: created a new `VoiceAsset` and `MediaAsset` through `espeak-ng`.
- Video render provider architecture with ffmpeg fallback and Creatomate implementation.
- Added regenerate endpoint for a single video asset.
- Pipeline smoke in `VIDEO_PROVIDER=ffmpeg`: upload reached `needs_review`, created `3` drafts, `3` voice assets, `3` video assets, and `3` preview assets.
- Regenerate video smoke passed: created a new `VideoAsset`, new video `MediaAsset`, and new preview asset through `ffmpeg`.
- Publishing provider architecture with mock publisher, VK adapter, Instagram manual package provider, and Yandex Maps manual package provider.
- Publication smoke in `PUBLISHER_PROVIDER=mock`: approval created `3` publication tasks and a run completed with `PublicationResult.status=published`.

## In Progress

- Next stage planning.

## Next

- Dashboard/provider visibility polish.
- Real VK media upload support for photos/videos.

## Blockers

- Push blocked: missing GitHub token in the non-interactive environment. `git push` failed because GitHub requested a password after Stage 1, Stage 2, Stage 3, Stage 4, Stage 5, and Stage 6 commits.
- Real OpenRouter vision requires `OPENROUTER_API_KEY` and a multimodal `OPENROUTER_VISION_MODEL`.
- Real OpenRouter text generation requires `OPENROUTER_API_KEY` and `OPENROUTER_TEXT_MODEL`.
- Real ElevenLabs TTS requires `ELEVENLABS_API_KEY` and `ELEVENLABS_VOICE_ID`.
- Real Yandex SpeechKit TTS requires `YANDEX_SPEECHKIT_API_KEY` and `YANDEX_SPEECHKIT_FOLDER_ID`.
- Real Creatomate rendering requires `CREATOMATE_API_KEY` and template ids.
- Real VK publishing requires `VK_ACCESS_TOKEN` and `VK_GROUP_ID`.

## Changelog

- 2026-05-15: Added vision provider package and OpenRouter-compatible image analysis adapter.
- 2026-05-15: Verified Docker rebuild, Alembic upgrade, health check, and upload pipeline smoke.
- 2026-05-15: Local commit created, push blocked by missing GitHub token.
- 2026-05-15: Added text generation provider package and OpenRouter-compatible persona copy adapter.
- 2026-05-15: Verified Docker rebuild, Alembic upgrade, health check, and text-provider upload pipeline smoke.
- 2026-05-15: Stage 2 local commit created, push still blocked by missing GitHub token.
- 2026-05-15: Added `POST /api/v1/content-drafts/{content_draft_id}/regenerate`.
- 2026-05-15: Verified regenerate endpoint creates a new version without overwriting the old draft.
- 2026-05-15: Stage 3 local commit created, push still blocked by missing GitHub token.
- 2026-05-15: Added TTS provider package and provider-backed voice generation.
- 2026-05-15: Added `POST /api/v1/voice-assets/{voice_asset_id}/regenerate`.
- 2026-05-15: Verified TTS pipeline smoke and voice regeneration smoke.
- 2026-05-15: Stage 4 local commit created, push still blocked by missing GitHub token.
- 2026-05-15: Added video render provider package and provider-backed ffmpeg rendering.
- 2026-05-15: Added `POST /api/v1/video-assets/{video_asset_id}/regenerate`.
- 2026-05-15: Verified Docker rebuild, Alembic upgrade, health check, video-provider upload pipeline smoke, and video regeneration smoke.
- 2026-05-15: Stage 5 local commit created, push still blocked by missing GitHub token.
- 2026-05-15: Added publishing provider package and provider-backed publication worker flow.
- 2026-05-15: Verified Docker rebuild, Alembic upgrade, health check, approval-to-publication task creation, and mock publication run.
- 2026-05-15: Stage 6 local commit created, push still blocked by missing GitHub token.
