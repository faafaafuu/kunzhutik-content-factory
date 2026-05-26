# System Architecture

## Why this stack

- `Python + FastAPI`: fast delivery, clean typing, strong ecosystem for AI/media automation.
- `SQLAlchemy 2 + Alembic`: explicit schema control and production migration flow.
- `Celery + Redis`: pragmatic async pipeline with retries and task routing.
- `PostgreSQL`: source of truth for content lifecycle and auditability.
- `MinIO/S3`: media asset storage abstraction.
- `aiogram`: Telegram moderation workflow with callback support.
- `ffmpeg` is planned for creative render stage.

## Module Boundaries

### Ingestion

- input validation
- object storage writes
- upload lifecycle
- task scheduling

### Vision Analysis

- visual feature extraction
- dish metadata
- scene mood and plating descriptors
- provider interface with local mock fallback and OpenRouter vision adapter

### Content Generation

- persona layer for `Кунжутик`
- per-platform copy generation
- scripts, CTA, short and long variants
- provider interface with local mock fallback and OpenRouter text generation adapter

### Creative Render

- layout templates
- mascot overlay
- aspect-ratio exports
- provider interface with ffmpeg fallback and Creatomate adapter
- final assembly layer; it does not generate live character animation

### AI Video Scenes

- `ScenePlan` describes a short 3D/cartoon reel as ordered scenes
- `AIVideoScene` tracks per-scene generation status and media asset output
- `AIVideoProvider` owns animated scene generation: character movement, emotion, camera, and mini-story beats
- current MVP provider is `mock`; future providers are `kling`, `runway`, then `pika`/`luma`
- `VIDEO_MODE=ai_video` is the primary upload pipeline: drafts create one ScenePlan, AIVideoProvider generates 3-4 animated scenes, TTS creates VoiceAsset, and final assembly only stitches scenes/subtitles/CTA
- `VIDEO_MODE=template` keeps the old ffmpeg/Creatomate story branch as a fallback

### Voice

- Russian TTS orchestration
- timing and pacing metadata
- provider interface with espeak fallback, ElevenLabs adapter, and Yandex SpeechKit adapter

### Moderation and Approval

- preview packaging
- Telegram dispatch
- approve/reject/regenerate actions

### Publishing

- platform adapters
- idempotent publish attempts
- result capture and audit trail
- provider interface with mock publisher, VK wall-post adapter, and manual packages for Instagram/Yandex Maps

## Data Lifecycle

Template branch:

`Upload -> MediaAsset -> AnalysisResult -> ContentDraft -> VoiceAsset -> VideoAsset -> ApprovalTask -> PublicationTask -> PublicationResult`

AI-video branch:

`Upload -> AnalysisResult -> ContentDraft -> ScenePlan -> AIVideoScene -> Final VideoAsset -> ApprovalTask -> PublicationTask -> PublicationResult`

Audit events are written on all state transitions.

## Evolution Strategy

Stage 1 keeps the workflow in one Python codebase with explicit modules.
Stage 2+ can split heavy modules into independent deployable services without changing the database contract.

## Provider Pattern

External integrations are added through provider packages. Each package keeps a base interface, schemas, mock/fallback implementation, real implementation, and factory. Provider choice is controlled by env, and mock providers remain available for local development.

Current provider packages:

- `app.providers.vision`: `mock` and `openrouter`
- `app.providers.text_generation`: `mock` and `openrouter`
- `app.providers.tts`: `mock/espeak-ng`, `elevenlabs`, and `yandex_speechkit`
- `app.providers.ai_video`: `mock`, `kling`, and `runway`
- `app.providers.video_render`: `ffmpeg` and `creatomate`
- `app.providers.publishing`: `mock`, `vk`, `instagram_manual`, `yandex_manual`
