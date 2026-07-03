# Kunzhutik Content Factory

Automated restaurant content pipeline around the character `Кунжутик`: dish photo in, ready-to-approve vertical AI video out.

## Current State

Full vertical slice works end to end:

`Upload -> MediaAsset -> AnalysisResult -> ContentDraft -> ScenePlan/AIVideoScene -> VoiceAsset -> VideoAsset -> ApprovalTask -> PublicationTask -> PublicationResult`

Every external capability sits behind a provider architecture with a local/mock fallback, switched via `.env`:

| Area | Providers | Env switch |
| --- | --- | --- |
| Vision (dish photo analysis) | OpenRouter, mock | `VISION_PROVIDER` |
| Text + scene plans | OpenRouter, mock | `TEXT_PROVIDER` |
| TTS | ElevenLabs, Yandex SpeechKit, espeak mock | `TTS_PROVIDER` |
| AI video scenes (primary) | fal.ai (Seedance/PixVerse/Kling via `AI_VIDEO_FAL_MODEL`), mock | `AI_VIDEO_PROVIDER` |
| Template video (legacy) | Creatomate, ffmpeg | `VIDEO_PROVIDER`, `VIDEO_MODE=template` |
| Publishing | VK (text post), Instagram/Yandex manual packages, mock | `PUBLISHER_PROVIDER` |

Without API keys everything runs on mocks/local fallbacks; `GENERATION_PROFILE=production` fails fast unless real providers are fully configured. Operator dashboard (auth, roles, provider diagnostics), Telegram approval bot, and Telegram storefront are included. See `docs/progress.md` for the detailed status log.

## Architecture Summary

Services:

- `api`: FastAPI control plane and operator-facing API
- `worker`: Celery background jobs for pipeline execution
- `telegram-bot`: aiogram bot for approval commands and callbacks
- `postgres`: primary relational storage
- `redis`: queues, broker, short-lived coordination
- `minio`: S3-compatible object storage for media assets

Planned service boundaries:

- `ingestion-service`
- `vision-analysis-service`
- `content-generation-service`
- `creative-render-service`
- `voice-service`
- `moderation-approval-service`
- `publishing-service`
- `admin-panel`

All of these currently live inside a single backend codebase with clean module boundaries to avoid premature distributed complexity.

## Repository Layout

```text
kunzhutik-content-factory/
├── docker-compose.yml
├── Makefile
├── docs/
│   └── architecture.md
├── infra/
│   └── scripts/
│       └── bootstrap_minio.sh
├── packages/
│   └── shared/
│       ├── pyproject.toml
│       └── src/shared/
├── services/
│   ├── api/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── alembic.ini
│   │   ├── alembic/
│   │   └── app/
│   ├── worker/
│   │   ├── Dockerfile
│   │   └── app/
│   └── telegram-bot/
│       ├── Dockerfile
│       └── app/
```

## Quick Start

1. Copy env file:

```bash
cp .env.example .env
```

2. Start the stack in the background:

```bash
docker compose up -d --build
```

All long-running containers use `restart: unless-stopped`, so Docker will bring them back after a crash or host reboot, unless you explicitly stop them.

3. Apply migrations:

```bash
docker compose exec api alembic upgrade head
```

Useful operations:

```bash
docker compose ps
docker compose logs -f telegram-bot
docker compose restart telegram-bot
```

4. Seed a default project and character:

```bash
curl -X POST http://localhost:8000/api/v1/bootstrap/default
```

5. Upload a dish photo:

```bash
curl -X POST http://localhost:8000/api/v1/uploads \
  -F project_id=<PROJECT_ID> \
  -F created_by=operator@example.com \
  -F file=@/absolute/path/to/dish.jpg
```

6. Check upload status:

```bash
curl http://localhost:8000/api/v1/uploads/<UPLOAD_ID>
```

## Main API Endpoints

- `GET /health`
- `POST /api/v1/bootstrap/default`
- `POST /api/v1/projects`
- `GET /api/v1/projects`
- `POST /api/v1/uploads`
- `GET /api/v1/uploads/{upload_id}`
- `GET /api/v1/uploads/{upload_id}/timeline`
- `POST /api/v1/approval-tasks/{approval_task_id}/dispatch`
- `POST /api/v1/approval-tasks/{approval_task_id}/decision`

## Workflow in Stage 1

1. Operator uploads a photo.
2. API stores the file in MinIO and creates `Upload` and `MediaAsset`.
3. Worker runs mocked analysis and persona text generation.
4. Worker creates `ContentDraft` records per platform.
5. Worker creates an `ApprovalTask`.
6. If Telegram env vars are configured, worker sends preview to approval chat.
7. Operator can approve or reject from Telegram or API.

## Roadmap

### Stage 1

- foundation, schema, queue, object storage, Telegram approval skeleton

### Stage 2

- real vision analysis adapter
- richer persona-layer prompt orchestration
- regeneration flows for text

### Stage 3

- TTS service
- script timeline generation
- video render templates and asset graph

### Stage 4

- publishing adapters for VK and Yandex Maps
- Instagram publication/preparation workflow
- retry, idempotency hardening, audit dashboards

### Stage 5

- operator dashboard on Next.js
- observability, Sentry, metrics, RBAC

## Notes

- Telegram approval is a real bot skeleton, but still lightweight.
- Publication to platforms is not implemented in Stage 1.
- Push to remote Git hosting requires configured remote credentials.
