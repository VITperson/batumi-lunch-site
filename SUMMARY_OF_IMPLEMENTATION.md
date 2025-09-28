# Summary of Implementation

## Backend
- FastAPI app (`backend/app/main.py`) со структурой:
  - `/auth/login`, `/auth/refresh`, `/auth/me` — JWT-аутентификация, роли `customer`/`admin`.
  - `/menu/week`, `/menu/order-window` — публичное меню с поддержкой следующей недели.
  - `/orders` CRUD: создание, обновление количества, отмена, фильтрация по пользователю и неделе (для админа).
  - `/admin/menu/*`, `/admin/order-window`, `/admin/broadcasts` — управление меню, окнами заказов, рассылками.
  - `/orders/calc` — поддержка многонедельного планировщика, возвращает разбивку по неделям.
  - `/healthz`, `/readyz` — мониторинг (проверка БД и Redis).
- SQLAlchemy модели и Alembic миграции для `users`, `orders`, `menu_weeks`, `menu_items`, `order_windows`, `broadcasts`.
- Доменные сервисы (`backend/app/domain`) переработаны из логики Telegram-бота: дедупликация заказов, антиспам, ценообразование.
- Redis rate limiting для `POST /orders` и `/admin/broadcasts`.
- Unit тесты (`backend/tests/unit/test_order_service.py`) и общие фикстуры (`backend/tests/conftest.py`).

## Scripts
- `scripts/migrate_json_to_db.py` — перенос JSON-хранилищ, идемпотентный UPSERT, журнал `logs/migrate_json_to_db.log`.
- `scripts/seed_menu.py` — сиды для меню, пользователей (admin/customer), окна заказов.

## Frontend
- Next.js 14 (App Router), React Query, Tailwind.
- Auth контекст с хранением access/refresh токенов, REST клиента.
- Страницы:
  - `/` — лендинг.
  - `/menu` — табличное меню недели, статус окна заказов.
  - `/login` — форма входа.
  - `/order/new` — трёхшаговый мастер заказа с обработкой 409.
  - `/account/orders`, `/orders/[id]` — управление заказами клиента.
  - `/admin`, `/admin/menu`, `/admin/reports`, `/admin/broadcast` — админ-панель.
- API-клиенты в `frontend/lib/api`, базовая инфраструктура для Cypress e2e (спеки с TODO).

## Infrastructure & CI
- Docker Compose с Postgres, Redis, MinIO, API, Web (`deploy/docker-compose.yml`).
- Dockerfile для backend (`deploy/Dockerfile.api`) и frontend (`deploy/Dockerfile.web`).
- GitHub Actions (`.github/workflows/ci.yml`) — линт/тест backend, lint/build frontend.

## Документация и артефакты
- `README.md` — пошаговый запуск, make-команды.
- `QA_CHECKLIST.md` — чек-лист smoke/regression.
- `OPEN_QUESTIONS.md` — нерешённые вопросы.
- `INTERNAL_NOTES.md` — соответствие FSM бота и веб-UI.
- `SUMMARY_OF_IMPLEMENTATION.md` — текущий документ.
