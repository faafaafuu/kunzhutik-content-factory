# Kunzhutik Progress

## Current Status

Working vertical slice is preserved:

`Upload -> MediaAsset -> AnalysisResult -> ContentDraft -> VoiceAsset / VideoAsset -> ApprovalTask -> PublicationTask -> PublicationResult`

Current step: Stage 2 completed locally, persona text generation provider architecture through OpenRouter.

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

## In Progress

- Commit and push for Stage 2.

## Next

- Stage 2: persona text generation provider architecture through OpenRouter.
- Stage 3: ContentDraft versioning and regenerate text endpoint.

## Blockers

- Push blocked: missing GitHub token in the non-interactive environment. `git push` failed because GitHub requested a password after Stage 1 and Stage 2 commits.
- Real OpenRouter vision requires `OPENROUTER_API_KEY` and a multimodal `OPENROUTER_VISION_MODEL`.
- Real OpenRouter text generation requires `OPENROUTER_API_KEY` and `OPENROUTER_TEXT_MODEL`.

## Changelog

- 2026-05-15: Added vision provider package and OpenRouter-compatible image analysis adapter.
- 2026-05-15: Verified Docker rebuild, Alembic upgrade, health check, and upload pipeline smoke.
- 2026-05-15: Local commit created, push blocked by missing GitHub token.
- 2026-05-15: Added text generation provider package and OpenRouter-compatible persona copy adapter.
- 2026-05-15: Verified Docker rebuild, Alembic upgrade, health check, and text-provider upload pipeline smoke.
- 2026-05-15: Stage 2 local commit created, push still blocked by missing GitHub token.
