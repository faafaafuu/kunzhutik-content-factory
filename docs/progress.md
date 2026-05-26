# Kunzhutik Progress

## Current Status

Working vertical slice is preserved:

`Upload -> MediaAsset -> AnalysisResult -> ContentDraft -> VoiceAsset / VideoAsset -> ApprovalTask -> PublicationTask -> PublicationResult`

Current step: Stage 10 complete, AI-video mode is now the primary upload pipeline; template rendering remains available behind `VIDEO_MODE=template`.

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
- Dashboard provider visibility: pipeline assets now expose `metadata_json`, and admin cards show provider/fallback/error/manual-package details.
- Provider diagnostics endpoint and dashboard panel for selected/effective provider status, fallback mode, and missing env names without exposing secrets.
- Real generation guardrails: `GENERATION_PROFILE=production` now fails before pipeline generation unless OpenRouter text, real TTS, Creatomate video, and fallback-off settings are configured.
- Improved local ffmpeg fallback readability with line wrapping, safer text layout, contrast/saturation pass, and vignette.
- AI-video foundation: `ScenePlan`, `AIVideoScene`, `AIVideoProvider`, mock scene generation, scene-plan endpoints, pipeline summary integration, and dashboard AI Video block.
- AI-video dashboard fix: one action can now create a ScenePlan, generate scenes, and render the final video instead of stopping at queued scenes.
- Unicode asset download fix: Cyrillic filenames now use RFC 5987 `filename*` encoding and no longer crash response headers.
- Upload pipeline now respects `VIDEO_MODE`: `ai_video` creates ScenePlan, AI-video scenes, VoiceAsset, final VideoAsset, and approval; `template` keeps the legacy ffmpeg/Creatomate branch.
- Final AI-video assembly now attaches the generated VoiceAsset and adds scene subtitles/CTA while using ffmpeg only as the assembly layer.

## In Progress

- Next stage planning.

## Next

- Connect real AI-video provider adapter: Kling first, Runway second. Current local `AI_VIDEO_PROVIDER=mock` proves orchestration only and does not produce real 3D animation.
- Extend TextGenerationProvider with real `generate_scene_plan()` via OpenRouter.
- Add Telegram actions for regenerate scene/full AI video.
- Real VK media upload support for photos/videos after generation quality is fixed.

## Blockers

- Real OpenRouter vision requires `OPENROUTER_API_KEY` and a multimodal `OPENROUTER_VISION_MODEL`.
- Real OpenRouter text generation requires `OPENROUTER_API_KEY` and `OPENROUTER_TEXT_MODEL`.
- Real ElevenLabs TTS requires `ELEVENLABS_API_KEY` and `ELEVENLABS_VOICE_ID`.
- Real Yandex SpeechKit TTS requires `YANDEX_SPEECHKIT_API_KEY` and `YANDEX_SPEECHKIT_FOLDER_ID`.
- Real Creatomate rendering requires `CREATOMATE_API_KEY` and template ids.
- Real Kling AI-video requires `KLING_API_KEY` and provider-specific API contract.
- Real Runway AI-video requires `RUNWAY_API_KEY` and provider-specific API contract.
- Real VK publishing requires `VK_ACCESS_TOKEN` and `VK_GROUP_ID`.
- Current Docker runtime still uses local/default providers until `.env` is updated and containers are recreated.

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
- 2026-05-16: Added dashboard provider/fallback visibility for analysis, drafts, assets, and publications.
- 2026-05-16: Verified Python compile, admin JavaScript syntax, Docker API rebuild, Alembic upgrade, health check, static admin JS, and pipeline metadata exposure.
- 2026-05-16: Stage 7 local commit created, push still blocked by missing GitHub token.
- 2026-05-25: Added `/api/v1/providers/diagnostics` and dashboard provider diagnostics panel.
- 2026-05-25: Verified Python compile, admin JavaScript syntax, Docker API rebuild, Alembic upgrade, health check, and authorized diagnostics response without secrets.
- 2026-05-25: Stage 8 local commit created, push still blocked; local branch remains ahead of `origin/main`.
- 2026-05-25: Added `GENERATION_PROFILE=production` guardrails and `.env.production.example`.
- 2026-05-25: Improved ffmpeg fallback text layout for readable local preview renders.
- 2026-05-25: Verified Docker API/worker rebuild, Alembic upgrade, health check, diagnostics production readiness flags, and production fail-fast validation.
- 2026-05-25: Stage 9 local commit created, push still blocked; local branch remains ahead of `origin/main`.
- 2026-05-25: GitHub token provided; pushed all local commits to `origin/main`.
- 2026-05-25: Added `ScenePlan` and `AIVideoScene` models with migration.
- 2026-05-25: Added `AIVideoProvider` package with mock, Kling stub, and Runway stub.
- 2026-05-25: Added scene-plan create/list/detail/regenerate/generate-scenes/render-final-video endpoints and dashboard AI Video block.
- 2026-05-25: Verified Python compile, admin JavaScript syntax, Docker API/worker rebuild, Alembic upgrade, health check, ScenePlan creation, mock scene generation, final VideoAsset render, pipeline summary integration, and single-scene regenerate.
- 2026-05-25: Fixed AI Video dashboard flow so `Generate full AI video` runs scene-plan creation, scene generation, and final rendering in sequence.
- 2026-05-25: Fixed asset download headers for Unicode filenames with `filename*=UTF-8''...`.
- 2026-05-25: Verified health check, Alembic upgrade, Python compile, admin JavaScript syntax, AI scene generation, final VideoAsset render for existing ScenePlan, pipeline summary, and Cyrillic asset download.
- 2026-05-26: Switched the primary worker path to `VIDEO_MODE=ai_video`; legacy template rendering now runs only when `VIDEO_MODE=template`.
- 2026-05-26: Added AI-video upload orchestration: ScenePlan creation, AIVideoProvider scene generation, VoiceAsset generation, final VideoAsset assembly with subtitles/CTA, and approval creation.
- 2026-05-26: Updated production guardrails so `GENERATION_PROFILE=production` rejects mock AI-video providers in `VIDEO_MODE=ai_video`.
- 2026-05-26: Verified Python compile, admin JavaScript syntax, Docker API/worker rebuild, Alembic upgrade, health check, runtime `VIDEO_MODE=ai_video`, and full upload smoke: 1 ScenePlan, 4 generated scenes, 1 VoiceAsset, 1 final `ai-final-video.mp4`, 1 ApprovalTask.
