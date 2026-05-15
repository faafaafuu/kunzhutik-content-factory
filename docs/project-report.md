# Kunzhutik Content Factory: структура, отчет и план работ

Дата отчета: 2026-05-15

## 1. Краткое описание проекта

`Kunzhutik Content Factory` - production-oriented система для ресторанного/food-проекта с персонажем `Кунжутик`.

Основные направления системы:

- прием фотографий блюд;
- хранение исходных и производных медиа;
- автоматический pipeline генерации контента;
- генерация текстов от имени персонажа `Кунжутик`;
- генерация voice/video/preview ассетов;
- Telegram approval;
- storefront для заказов еды;
- Telegram-адаптированная витрина `/tg`;
- operator dashboard;
- подготовка публикаций по платформам.

Сейчас проект уже содержит рабочий вертикальный срез:

`Upload -> MediaAsset -> AnalysisResult -> ContentDraft -> VoiceAsset/VideoAsset -> ApprovalTask -> PublicationTask -> PublicationResult`

Параллельно реализован storefront order flow:

`Telegram bot -> /tg storefront -> StoreOrder -> Telegram operator notification -> status callbacks -> customer status updates`

## 2. Текущий стек

Backend:

- Python 3.11
- FastAPI
- SQLAlchemy
- Alembic
- Pydantic Settings

Async/background:

- Celery
- Redis broker/result backend

Storage:

- PostgreSQL
- MinIO / S3-compatible object storage

Telegram:

- aiogram
- Telegram Bot API
- Telegram WebApp API на frontend

Media:

- ffmpeg
- espeak-ng
- SVG mascot/assets

Frontend:

- Vanilla HTML/CSS/JS для storefront и dashboard
- Telegram WebApp адаптация через `telegram-web-app.js`

Infra:

- Docker
- Docker Compose
- env-based config

## 3. Полная структура репозитория

```text
kunzhutik-content-factory/
├── .env
├── .env.example
├── .github/
│   └── .keep
├── .gitignore
├── Makefile
├── README.md
├── docker-compose.yml
├── docs/
│   ├── architecture.md
│   └── project-report.md
├── infra/
│   ├── caddy/
│   │   └── Caddyfile
│   └── scripts/
│       └── bootstrap_minio.sh
├── packages/
│   └── shared/
│       ├── pyproject.toml
│       └── src/
│           └── shared/
│               ├── __init__.py
│               └── enums.py
├── services/
│   ├── api/
│   │   ├── Dockerfile
│   │   ├── alembic.ini
│   │   ├── requirements.txt
│   │   ├── alembic/
│   │   │   ├── env.py
│   │   │   ├── script.py.mako
│   │   │   └── versions/
│   │   │       ├── 20260423_0001_initial_schema.py
│   │   │       ├── 20260423_0002_storefront_orders.py
│   │   │       ├── 20260423_0003_storefront_payment_method.py
│   │   │       └── 20260514_0004_operator_users.py
│   │   └── app/
│   │       ├── __init__.py
│   │       ├── main.py
│   │       ├── worker_tasks.py
│   │       ├── api/
│   │       │   ├── __init__.py
│   │       │   ├── deps.py
│   │       │   └── routes/
│   │       │       ├── __init__.py
│   │       │       ├── approvals.py
│   │       │       ├── auth.py
│   │       │       ├── bootstrap.py
│   │       │       ├── health.py
│   │       │       ├── projects.py
│   │       │       ├── publications.py
│   │       │       ├── storefront.py
│   │       │       └── uploads.py
│   │       ├── core/
│   │       │   ├── __init__.py
│   │       │   ├── celery_app.py
│   │       │   └── config.py
│   │       ├── db/
│   │       │   ├── __init__.py
│   │       │   ├── base.py
│   │       │   └── session.py
│   │       ├── models/
│   │       │   ├── __init__.py
│   │       │   ├── all_models.py
│   │       │   ├── analysis_result.py
│   │       │   ├── approval_task.py
│   │       │   ├── audit_event.py
│   │       │   ├── character_profile.py
│   │       │   ├── content_draft.py
│   │       │   ├── media_asset.py
│   │       │   ├── mixins.py
│   │       │   ├── project.py
│   │       │   ├── publication_result.py
│   │       │   ├── publication_task.py
│   │       │   ├── store_order.py
│   │       │   ├── upload.py
│   │       │   ├── video_asset.py
│   │       │   └── voice_asset.py
│   │       ├── repositories/
│   │       ├── schemas/
│   │       │   ├── __init__.py
│   │       │   ├── approval.py
│   │       │   ├── common.py
│   │       │   ├── project.py
│   │       │   ├── publication.py
│   │       │   ├── storefront.py
│   │       │   └── upload.py
│   │       ├── services/
│   │       │   ├── __init__.py
│   │       │   ├── approvals.py
│   │       │   ├── audit.py
│   │       │   ├── bootstrap.py
│   │       │   ├── character.py
│   │       │   ├── media_generation.py
│   │       │   ├── notifications.py
│   │       │   ├── publications.py
│   │       │   ├── storage.py
│   │       │   ├── storefront.py
│   │       │   ├── uploads.py
│   │       │   ├── vision_analysis.py
│   │       │   └── workflow.py
│   │       ├── store/
│   │       │   ├── __init__.py
│   │       │   └── catalog.py
│   │       └── web/
│   │           ├── admin.html
│   │           ├── admin.js
│   │           ├── app.js
│   │           ├── index.html
│   │           ├── styles.css
│   │           └── assets/
│   │               ├── kunzhutik-mascot.svg
│   │               └── menu/
│   │                   ├── baklava.svg
│   │                   ├── bubble.svg
│   │                   ├── coffee.svg
│   │                   ├── combo.svg
│   │                   ├── dessert.svg
│   │                   ├── doner.svg
│   │                   ├── drink.svg
│   │                   ├── fries.svg
│   │                   ├── salad.svg
│   │                   ├── seasonal.svg
│   │                   └── soup.svg
│   ├── telegram-bot/
│   │   ├── Dockerfile
│   │   └── bot_main.py
│   └── worker/
│       ├── Dockerfile
│       └── app/
│           └── celery_app.py
```

Примечание: `__pycache__`, `.git` и runtime artifacts не являются частью продуктовой структуры и не описываются как рабочие модули.

## 4. Архитектура по модулям

### 4.1. `api`

FastAPI control plane. Отвечает за:

- HTTP API;
- storefront pages;
- operator dashboard;
- создание uploads/orders;
- доступ к pipeline summary;
- approval/publication endpoints;
- подключение router'ов;
- отдачу static frontend.

Ключевые router'ы:

- `health.py` - health-check;
- `bootstrap.py` - создание default project/character;
- `projects.py` - проекты;
- `uploads.py` - upload, assets, timeline, pipeline summary;
- `approvals.py` - dispatch/decision по approval;
- `publications.py` - список и запуск publication tasks;
- `storefront.py` - storefront, Telegram storefront, orders API.

### 4.2. `worker`

Celery worker. Сейчас использует задачи из `services/api/app/worker_tasks.py`.

Задачи:

- `app.tasks.process_upload_pipeline`;
- `app.tasks.dispatch_approval_preview`;
- `app.tasks.publish_publication_task`.

### 4.3. `telegram-bot`

aiogram bot. Отвечает за:

- клиентские команды `/start`, `/menu`, `/contacts`;
- кнопку открытия storefront;
- operator команды `/orders`, `/pending`;
- callback управления заказами;
- callback approval;
- прием `web_app_data` после создания заказа.

### 4.4. `packages/shared`

Общие enum'ы:

- `PipelineStatus`;
- `ContentPlatform`;
- `DraftKind`;
- `AssetKind`;
- `ApprovalStatus`;
- `ApprovalTrigger`;
- `PublicationStatus`.

### 4.5. `infra`

Скрипты инфраструктуры:

- bootstrap MinIO bucket.
- Caddy reverse proxy для временного HTTPS-домена.

## 5. Сущности данных

Реализованные модели:

- `Project` - проект/бренд;
- `CharacterProfile` - персонаж `Кунжутик`;
- `Upload` - набор загруженных фото;
- `MediaAsset` - исходные и производные файлы;
- `AnalysisResult` - результат vision analysis;
- `ContentDraft` - тексты/сценарии под платформы;
- `VoiceAsset` - voice/TTS asset;
- `VideoAsset` - video/render asset;
- `ApprovalTask` - задача согласования;
- `PublicationTask` - задача публикации;
- `PublicationResult` - результат публикации;
- `AuditEvent` - audit/timeline события;
- `StoreOrder` - заказ через storefront.

## 6. Реализованный content pipeline

### 6.1. Upload

Оператор загружает файл через:

```text
POST /api/v1/uploads
```

Что происходит:

- проверяется проект;
- файл читается из multipart form;
- создается `Upload` со статусом `queued`;
- файл сохраняется в MinIO;
- создается `MediaAsset` с kind `source_photo`;
- пишется audit event `upload.created`;
- в Celery отправляется `process_upload_pipeline`.

### 6.2. Worker pipeline

Celery task:

```text
app.tasks.process_upload_pipeline
```

Шаги:

1. Переводит upload в `processing`.
2. Запускает `vision-analysis-service`.
3. Создает `AnalysisResult`.
4. Создает drafts для:
   - Instagram;
   - VK;
   - Yandex Maps.
5. Генерирует voice/video/preview assets.
6. Создает `ApprovalTask`.
7. Переводит upload в `needs_review`.
8. При configured Telegram approval chat может отправить preview.

### 6.3. Vision analysis

Сервис:

```text
services/api/app/services/vision_analysis.py
```

Режимы:

- `VISION_ANALYSIS_PROVIDER=mock` - безопасный локальный режим без внешних API;
- `VISION_ANALYSIS_PROVIDER=openai` - real vision adapter через OpenAI Responses API.

Сервис извлекает:

- dish name;
- вероятные ingredients;
- visual mood;
- plating style;
- composition/lighting/camera angle/hero element/colors;
- content warnings;
- confidence;
- raw provider metadata.

Если real provider недоступен, не настроен или вернул ошибку, worker автоматически падает обратно на `mock-vision-v1` и сохраняет `fallback_reason` в `raw_payload`.

### 6.4. Media generation

Сервис:

```text
services/api/app/services/media_generation.py
```

Сейчас реализовано:

- voice через `espeak-ng`;
- video через `ffmpeg`;
- preview frame через `ffmpeg`;
- mascot overlay;
- вертикальные 9:16 видео;
- fallback rendering без source image, если файл не поддерживается как изображение.

### 6.5. Pipeline summary

Endpoint:

```text
GET /api/v1/uploads/{upload_id}/pipeline
```

Возвращает:

- upload;
- analysis results;
- drafts;
- approvals;
- publication tasks;
- publication results;
- assets;
- timeline.

Это основной endpoint для operator dashboard.

## 7. Реализованный approval flow

### 7.1. API approval

Endpoints:

```text
POST /api/v1/approval-tasks/{approval_task_id}/dispatch
POST /api/v1/approval-tasks/{approval_task_id}/decision
```

Поддерживаемые решения:

- `approved`;
- `rejected`;
- `regenerate_requested`.

После `approved`:

- upload получает статус `completed`;
- создаются `PublicationTask` по каждому `ContentDraft`;
- пишется audit event.

После `rejected` или `regenerate_requested`:

- upload остается/становится `needs_review`;
- пишется audit event.

### 7.2. Telegram approval

Команда:

```text
/pending
```

Показывает pending/dispatched approval tasks с preview:

- блюдо;
- platform/kind;
- caption;
- CTA.

Кнопки:

- Approve;
- Reject;
- Regenerate.

## 8. Реализованный publishing flow

### 8.1. Publication task creation

После approval `approved` создаются publication tasks:

- Instagram;
- VK;
- Yandex Maps.

Idempotency key:

```text
draft:{content_draft_id}:v{version}:{platform}
```

Это защищает от дублей при повторном approve.

### 8.2. Publication API

Endpoints:

```text
GET /api/v1/publication-tasks
GET /api/v1/publication-tasks?upload_id={upload_id}
POST /api/v1/publication-tasks/{publication_task_id}/run
```

### 8.3. Mock publication adapter

Celery task:

```text
app.tasks.publish_publication_task
```

Сейчас это mock adapter:

- переводит task в `publishing`;
- увеличивает `attempt_count`;
- создает `PublicationResult`;
- переводит task в `published`;
- генерирует mock `remote_url`.

Это сознательно оставлено как mock, потому что реальные VK/Yandex/Instagram adapters требуют credentials, review и platform-specific ограничения.

## 9. Реализованный storefront order flow

### 9.1. Storefront

Основная витрина:

```text
GET /
```

Telegram-адаптированная витрина:

```text
GET /tg
```

API меню:

```text
GET /api/v1/store/menu
```

Создание заказа:

```text
POST /api/v1/store/orders
```

Список заказов:

```text
GET /api/v1/store/orders
```

Смена статуса:

```text
PATCH /api/v1/store/orders/{order_id}
```

### 9.2. StoreOrder

Заказ хранит:

- имя клиента;
- телефон;
- адрес;
- слот доставки;
- способ оплаты;
- комментарий;
- статус;
- сумму;
- items JSON;
- source JSON с customer profile и status history.

### 9.3. Telegram customer profile

Поддержаны два варианта:

- `telegram_link` - профиль из подписанной ссылки бота;
- `telegram` - профиль из Telegram WebApp `initDataUnsafe`.

Для `telegram_link` backend проверяет HMAC-подпись через bot token.

### 9.4. Operator notifications

При создании заказа оператор получает Telegram message с inline-кнопками:

- `Принять`;
- `Готовится`;
- `В доставке`;
- `Выполнен`;
- `Отмена`.

### 9.5. Customer notifications

Если customer Telegram profile верифицирован, клиент получает:

- сообщение о получении заказа;
- обновления статуса заказа.

## 10. Telegram bot

Клиентские команды:

- `/start`;
- `/menu`;
- `/contacts`.

Операторские команды:

- `/orders`;
- `/pending`.

Клиентские команды открыты для пользователей. Операторские команды защищены allowlist через:

```text
TELEGRAM_ALLOWED_USER_IDS
```

Кнопка storefront:

- ведет на `/tg`;
- если URL начинается с `https://`, используется Telegram `WebAppInfo`;
- если URL начинается с `http://`, используется обычная URL-кнопка.

Важное ограничение:

Telegram embedded WebApp требует HTTPS. При текущем `APP_BASE_URL=http://84.247.166.53:8000` бот может открыть только обычную ссылку, не встроенное приложение. Для embedded mode нужно настроить HTTPS-домен и указать его в `APP_BASE_URL` или `TELEGRAM_APPROVAL_BASE_URL`.

## 11. Operator dashboard

Адрес:

```text
GET /admin/orders
```

Несмотря на старый путь, страница теперь является полноценным operator dashboard. Доступ закрыт session-cookie авторизацией.

Login:

```text
GET /admin/login
POST /api/v1/auth/login
POST /api/v1/auth/logout
GET /api/v1/auth/me
```

Роли:

- `operator`;
- `admin`.

Вкладки:

- `Content Pipeline`;
- `Store Orders`.

Возможности `Content Pipeline`:

- выбрать проект;
- загрузить фото;
- увидеть список uploads;
- открыть upload summary;
- увидеть analysis;
- увидеть drafts;
- увидеть assets;
- увидеть timeline;
- approve/reject/regenerate;
- увидеть publication tasks;
- запустить publication task.

Возможности `Store Orders`:

- видеть заказы;
- видеть состав заказа;
- менять статус.

## 12. Frontend storefront

Файлы:

- `services/api/app/web/index.html`;
- `services/api/app/web/app.js`;
- `services/api/app/web/styles.css`;
- `services/api/app/web/assets/*`.

Что есть:

- темная современная палитра;
- адаптивная верстка;
- категории;
- карточки меню;
- корзина;
- checkout drawer;
- Telegram quick auth;
- Telegram mode на `/tg`;
- Telegram WebApp theme colors;
- Telegram haptics/main button/sendData.

## 13. Docker services

Основные сервисы:

- `api`;
- `worker`;
- `telegram-bot`;
- `postgres`;
- `redis`;
- `minio`;
- `create-bucket`.

Типовой запуск:

```bash
docker compose up -d --build
```

Миграции:

```bash
docker compose exec api alembic upgrade head
```

Проверка:

```bash
docker compose ps
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f telegram-bot
```

## 14. API endpoints

Health:

```text
GET /health
```

Projects:

```text
GET /api/v1/projects
POST /api/v1/projects
POST /api/v1/bootstrap/default
```

Uploads:

```text
GET /api/v1/uploads
POST /api/v1/uploads
GET /api/v1/uploads/{upload_id}
GET /api/v1/uploads/{upload_id}/timeline
GET /api/v1/uploads/{upload_id}/assets
GET /api/v1/uploads/{upload_id}/assets/{asset_id}/download
GET /api/v1/uploads/{upload_id}/pipeline
```

Approvals:

```text
POST /api/v1/approval-tasks/{approval_task_id}/dispatch
POST /api/v1/approval-tasks/{approval_task_id}/decision
```

Publications:

```text
GET /api/v1/publication-tasks
GET /api/v1/publication-tasks?upload_id={upload_id}
POST /api/v1/publication-tasks/{publication_task_id}/run
```

Storefront:

```text
GET /
GET /tg
GET /admin/orders
GET /api/v1/store/menu
POST /api/v1/store/orders
GET /api/v1/store/orders
PATCH /api/v1/store/orders/{order_id}
```

## 15. Что было сделано по задачам

### Foundation

Сделано:

- monorepo/repo bootstrap;
- Docker Compose;
- FastAPI backend;
- PostgreSQL schema;
- Alembic migrations;
- Redis;
- Celery worker;
- MinIO;
- Telegram bot skeleton;
- базовые модели;
- базовые services/schemas/routes.

### Storefront design iterations

Сделано:

- несколько итераций дизайна страницы;
- современная темная палитра;
- gradient backgrounds;
- responsive layout;
- карточки меню;
- корзина;
- checkout drawer;
- skeleton/error/empty states.

Ключевые коммиты:

```text
928c2bf feat: add playful storefront variant
eced3fd refine storefront palette and auth icons
f5f717b feat: modernize storefront layout
6bcdebd feat: add dark gradient storefront theme
2a834e8 feat: polish storefront states
```

### Задача 2: Telegram order flow

Коммит:

```text
5ce9dac feat: add telegram order flow
```

Сделано:

- операторские Telegram notifications;
- inline buttons для статусов заказа;
- команда `/orders`;
- статусная история заказа;
- customer notification при верифицированном Telegram profile;
- общий backend status flow.

### Задача 3: Pipeline summary

Коммит:

```text
16f3d06 feat: expose upload pipeline summary
```

Сделано:

- `GET /uploads/{id}/pipeline`;
- summary по analysis/drafts/approval/assets/timeline;
- обновление upload status после approval;
- улучшенный `/pending` в Telegram.

### Задача 4: Publication task flow

Коммит:

```text
887c9c9 feat: add publication task flow
```

Сделано:

- `PublicationTask` creation после approve;
- idempotency key;
- publication API;
- Celery publication task;
- mock publication adapter;
- `PublicationResult`.

### Задача 5: Operator dashboard

Коммит:

```text
53e3a95 feat: add operator pipeline dashboard
```

Сделано:

- dashboard на `/admin/orders`;
- tabs content/orders;
- upload form;
- upload list;
- pipeline detail;
- approval actions;
- publication run actions;
- store orders tab.

### Telegram storefront mode

Коммит:

```text
4596e5a feat: add telegram storefront mode
```

Сделано:

- `/tg` route;
- Telegram-адаптированная storefront верстка;
- bot button на `/tg`;
- client commands без allowlist;
- operator commands с allowlist;
- Telegram WebApp theme/haptics/sendData.

### HTTPS для Telegram WebApp

Коммит:

```text
87dc1db feat: add https reverse proxy for telegram webapp
afd8f67 fix: set public dns for caddy acme
```

Сделано:

- добавлен `docker-compose.https.yml`;
- добавлен Caddy reverse proxy;
- настроен временный HTTPS-домен через `sslip.io`;
- проверена выдача Let's Encrypt сертификата;
- Telegram WebApp может использовать HTTPS URL.

### Auth/RBAC для dashboard

Коммит:

```text
615e2cf feat: add dashboard auth and role guards
```

Сделано:

- модель `OperatorUser`;
- миграция `20260514_0004_operator_users.py`;
- password hashing;
- session cookie;
- login page `/admin/login`;
- закрыт `/admin/orders`;
- закрыты write/read API для dashboard;
- роли `operator/admin`;
- bootstrap admin через env.

### Vision analysis adapter

Коммит:

```text
будет создан после текущей задачи
```

Сделано:

- вынесен `VisionAnalyzer` interface;
- добавлен `MockVisionAnalyzer`;
- добавлен `OpenAIVisionAnalyzer`;
- добавлены env-настройки provider/model/timeout/detail;
- worker использует provider metadata в `AnalysisResult`;
- Telegram preview получает `analysis_provider` и `mock`;
- проверен vertical smoke: upload перешел в `needs_review`, создано `3` drafts, `1` approval, `10` assets.

## 16. Текущий статус Git

Последние релевантные коммиты:

```text
615e2cf feat: add dashboard auth and role guards
afd8f67 fix: set public dns for caddy acme
87dc1db feat: add https reverse proxy for telegram webapp
4596e5a feat: add telegram storefront mode
53e3a95 feat: add operator pipeline dashboard
887c9c9 feat: add publication task flow
16f3d06 feat: expose upload pipeline summary
5ce9dac feat: add telegram order flow
2a834e8 feat: polish storefront states
6bcdebd feat: add dark gradient storefront theme
f5f717b feat: modernize storefront layout
eced3fd refine storefront palette and auth icons
928c2bf feat: add playful storefront variant
```

Важное замечание:

- `origin/main` в локальном логе отстает от текущего `main`;
- push не выполнялся из-за отсутствия GitHub token в окружении;
- есть локальные незакоммиченные изменения в `Makefile`, `README.md`, `docker-compose.yml`, которые ранее не трогались, потому что они были вне текущих задач.

## 17. Что сейчас является mock/stub

Mock/stub части:

- `vision-analysis-service` имеет mock по умолчанию и optional OpenAI adapter;
- `content-generation-service` пока deterministic persona templates;
- `voice-service` использует `espeak-ng`, не production TTS provider;
- `creative-render-service` работает через базовые ffmpeg templates;
- `publishing-service` использует mock adapter;
- Instagram/VK/Yandex Maps реальные adapters не подключены;
- OAuth VK/Google в storefront не подключен;
- RBAC/security dashboard реализованы базово, без CSRF hardening и расширенной policy;
- HTTPS для Telegram WebApp настроен временно через `sslip.io`; нужен постоянный домен.

## 18. Основные риски и ограничения

### 18.1. Telegram WebApp требует HTTPS

Временное решение уже настроено через Caddy и `sslip.io`. Для production нужен постоянный домен, DNS и стабильная reverse-proxy конфигурация.

### 18.2. Dashboard security hardening

Базовая авторизация уже включена. Для production нужно добавить:

- CSRF/CORS policy;
- audit actor binding.
- rate limit на login;
- управление пользователями в admin UI.

### 18.3. Publication adapters

Реальные публикации требуют:

- credentials;
- platform review;
- API limits;
- platform-specific media restrictions;
- retry/idempotency hardening;
- manual fallback flow для Instagram.

### 18.4. TTS/render quality

Текущий `espeak-ng` достаточен для pipeline smoke, но не для final brand voice. Нужно заменить на production TTS.

### 18.5. Secrets management

Сейчас конфигурация через `.env`. Для production нужны:

- secret manager;
- ограничение доступа к `.env`;
- rotation policy;
- separate env per stage.

## 19. Предстоящие работы

### Приоритет 1: Persona/content generation layer

Задачи:

- вынести prompt templates;
- использовать `CharacterProfile.persona_prompt`;
- генерировать варианты:
- short;
- long;
- caption;
- CTA;
- script;
- учитывать platform constraints:
- Instagram post/reels/stories;
- VK post/clips/stories;
- Yandex Maps news;
- добавить regenerate text для draft;
- версионировать drafts.

Критерий готовности:

- тексты создаются через persona layer;
- можно regenerate конкретный draft;
- новая версия не затирает старую.

### Приоритет 2: Production TTS

Задачи:

- выбрать TTS provider;
- добавить provider abstraction;
- добавить настройки voice/speaking rate/pitch/style;
- добавить regenerate voice;
- сохранять provider payload;
- ограничить длину script.

Критерий готовности:

- voice звучит живо и подходит персонажу;
- voice regeneration работает по конкретному draft.

### Приоритет 3: Render templates

Задачи:

- формализовать template registry;
- добавить форматы 9:16 story/reel/clip и 1:1 post;
- добавить template params;
- добавить safe text layout;
- добавить brand assets;
- добавить mascot positioning rules;
- добавить regenerate video;
- добавить preview thumbnails.

Критерий готовности:

- для каждой платформы есть корректный формат;
- video assets проходят визуальную проверку;
- regenerate video работает без пересоздания всего pipeline.

### Приоритет 4: Реальные publishing adapters

Задачи:

- VK adapter: posts, clips, stories where available;
- Yandex Maps adapter: photos, news/posts;
- Instagram workflow: prepare assets/manual package/direct integration if available;
- retry policy;
- idempotency;
- rate limits;
- error handling.

Критерий готовности:

- публикации уходят хотя бы в VK/Yandex;
- результат сохраняет real remote id/url;
- failures видны в dashboard.

### Приоритет 5: Dashboard v2

Задачи:

- перейти на Next.js или оставить static, если хватает;
- добавить filtering/search;
- добавить detail pages: uploads/orders/publications;
- добавить asset preview inline;
- добавить video player;
- добавить timeline view;
- добавить retry buttons;
- добавить regenerate buttons.

Критерий готовности:

- оператор может вести полный цикл без API/curl.

### Приоритет 6: Observability

Задачи:

- structured logging;
- request id;
- task id correlation;
- Sentry;
- Prometheus metrics;
- health checks по dependent services;
- alerting.

Критерий готовности:

- можно быстро понять, где сломался pipeline;
- ошибки worker/API видны без ручного чтения контейнера.

### Приоритет 7: Tests/CI

Задачи:

- pytest для services;
- integration tests через test containers или docker compose;
- frontend smoke tests;
- lint/format;
- GitHub Actions;
- migration tests.

Критерий готовности:

- PR/commit проверяет базовую работоспособность pipeline.

### Отдельно: Production domain/security

Задачи:

- заменить временный `sslip.io` на постоянный домен;
- добавить CSRF/rate-limit для dashboard auth;
- добавить управление пользователями;
- вынести secrets в secret manager.

## 20. Рекомендованный ближайший порядок работ

1. Добавить persona generation service с regenerate text.
2. Подключить production TTS.
3. Улучшить render templates и 1:1 формат.
4. Реализовать VK publication adapter.
5. Реализовать Yandex Maps adapter.
6. Добавить Dashboard v2 controls для regenerate/retry.
7. Добавить tests/CI/observability.
8. Заменить временный HTTPS-домен на постоянный.

## 21. Команды для быстрой проверки

Запуск:

```bash
docker compose up -d --build
```

Миграции:

```bash
docker compose exec api alembic upgrade head
```

Health:

```bash
curl http://localhost:8000/health
```

Bootstrap:

```bash
curl -X POST http://localhost:8000/api/v1/bootstrap/default
```

Storefront:

```text
http://localhost:8000/
http://localhost:8000/tg
http://localhost:8000/admin/orders
```

Pipeline upload:

```bash
curl -X POST http://localhost:8000/api/v1/uploads \
  -F project_id=<PROJECT_ID> \
  -F created_by=operator@example.com \
  -F notes='test upload' \
  -F file=@/absolute/path/to/dish.jpg
```

Pipeline summary:

```bash
curl http://localhost:8000/api/v1/uploads/<UPLOAD_ID>/pipeline
```

Publication tasks:

```bash
curl http://localhost:8000/api/v1/publication-tasks?upload_id=<UPLOAD_ID>
```

Run publication:

```bash
curl -X POST http://localhost:8000/api/v1/publication-tasks/<PUBLICATION_TASK_ID>/run \
  -H 'Content-Type: application/json' \
  -d '{"actor":"operator"}'
```

## 22. Итог

Проект уже прошел путь от foundation до работающего vertical slice:

- есть инфраструктура;
- есть БД и модели;
- есть загрузка фото;
- есть worker pipeline;
- есть генерация mock analysis/content/media;
- есть Telegram approval;
- есть storefront order flow;
- есть Telegram storefront mode;
- есть operator dashboard;
- есть временный HTTPS reverse proxy;
- есть dashboard auth/RBAC;
- есть pluggable vision-analysis adapter;
- есть publication task flow.

Главные production blockers сейчас:

- временный HTTPS-домен нужно заменить постоянным;
- content/TTS/publication adapters пока не production providers;
- нет CI/tests/observability.

Следующий технически правильный шаг: persona/content generation layer с версионированием и regenerate text.
