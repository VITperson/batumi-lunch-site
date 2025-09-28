# Batumi Lunch Web Platform

Batumi Lunch Web — переезд Telegram-бота по доставке обедов на полноценный веб-стек. Репозиторий включает FastAPI backend, Next.js frontend, PostgreSQL/Redis инфраструктуру и вспомогательные скрипты миграции.

## Состав репозитория

- `backend/` — FastAPI-приложение, доменная логика, Alembic-миграции, unit и интеграционные тесты.
- `frontend/` — Next.js 14 (App Router), React Query, Tailwind UI. Содержит клиентскую логику, экраны заказов и админку.
- `deploy/` — Dockerfile'ы и `docker-compose.yml` для локального запуска API, web, Postgres, Redis, MinIO.
- `scripts/` — `migrate_json_to_db.py` и `seed_menu.py` для переноса и наполнения данных.
- `.github/workflows/ci.yml` — минимальный CI: lint/tests backend, build frontend.

## Требования

- Python 3.13 (локально можно 3.12 для разработки/CI).
- Node.js 20.
- PostgreSQL 15+ и Redis 7 (локально поднимаются Docker Compose).
- MinIO (поднимается `docker compose`).

## Быстрый старт

```bash
cp .env.sample .env.local
make install            # pip install -e backend[dev] + npm install
make up                 # docker compose up -d (postgres, redis, minio, api, web)
```

Либо запустить вручную:

```bash
make migrate            # alembic upgrade head
make seed               # скрипт с тестовыми данными
make serve-api          # uvicorn app.main:app --reload
make serve-web          # next dev
```

API доступен на `http://localhost:8000`, фронтенд — `http://localhost:3000`.

## Make команды

| Команда            | Описание |
| ------------------ | -------- |
| `make install`     | Установка Python и Node зависимостей.
| `make migrate`     | Alembic миграции (`alembic upgrade head`).
| `make seed`        | Первичное наполнение меню/пользователей.
| `make serve-api`   | Запуск FastAPI (uvicorn).
| `make serve-web`   | Запуск Next.js dev-сервера.
| `make lint`        | `ruff check` + `mypy` для backend.
| `make test`        | `pytest` для backend.
| `make openapi`     | Генерация `openapi.json` (для фронтенда и документации).
| `make up`/`make down` | Docker-compose инфраструктура.

## Миграция данных из Telegram-бота

1. Поместите `users.json`, `orders.json`, `menu.json`, `order_window.json` в корень проекта.
2. Выполните `python scripts/migrate_json_to_db.py` — скрипт идемпотентен, прогресс пишется в `logs/migrate_json_to_db.log`.
3. Для тестового наполнения используйте `python scripts/seed_menu.py`.

## Тестирование

- Backend: `make lint`, `make test` — покрывают доменные сервисы, API-интеграции, mypy.
- Frontend: `npm run lint`, `npm run build`. E2E-спеки в `frontend/e2e` помечены `it.skip` и ждут внедрения тестовой среды.
- Docker: `make up` поднимает стек; после старта выполните smoke-сценарии (`/menu`, `/order/new`, админ-панель).

## CI

GitHub Actions (`.github/workflows/ci.yml`):
- `backend` job — установка зависимостей, `ruff`, `mypy`, `pytest`.
- `frontend` job — Node 20, `npm install`, `next lint`, `next build`.

## Статичные артефакты

- OpenAPI: `backend/openapi.json` (генерируется через `make openapi`).
- QA чек-лист: `QA_CHECKLIST.md`.
- Summary: `SUMMARY_OF_IMPLEMENTATION.md`.
- Открытые вопросы: `OPEN_QUESTIONS.md`.

## Полезные ссылки

- API health-checks: `GET /healthz`, `GET /readyz`.
- Основные REST endpoints описаны в `roadmap.md` и реализованы в `backend/app/api/v1`.
- UI-флоу соответствуют FSM бота (см. `INTERNAL_NOTES.md`).
