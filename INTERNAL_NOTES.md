# Internal Notes — Batumi Lunch Web Migration

## Tech Stack & Platform Decisions
- Frontend: Next.js (React) SPA with SSR; Node 20+ runtime; Chakra UI or MUI allowed per roadmap (exact choice TBD → see TODO).
- Backend: FastAPI (Python 3.13) with modular structure (core/settings, api/v1, domain services, db models, workers).
- Persistence: PostgreSQL 15+ (SQLAlchemy via async engine); Redis for sessions/rate limiting; MinIO (S3-compatible) for menu photos; local `.env` for development only.
- Messaging/Workers: Celery or RQ workers for broadcasts & async tasks; REST-first API; OpenAPI contract + generated TS client for frontend.
- Auth: JWT (access + refresh) with refresh in httpOnly cookie; roles `customer` and `admin`; admins linked to Telegram IDs for coexistence.
- Observability: JSON logs with trace-id, Prometheus metrics, Sentry-style error tracking, `/healthz` and `/readyz` endpoints.

## Key API Contracts (v1)
- `GET /api/v1/menu/week?date=YYYY-MM-DD` → `{week, items[]}`; 404 if absent.
- `POST /api/v1/orders` → `{orderId, status}`; validates `{day, count, address, phone, weekStart}`; errors: 400/409/422.
- `PATCH /api/v1/orders/{id}` → partial update `{count}` or `{address}`; errors: 403/404/409.
- `POST /api/v1/orders/{id}/cancel` → `{orderId, status}`; errors: 403/404.
- `GET /api/v1/orders?mine=1|week=...` → list; errors: 401/500.
- `POST /api/v1/admin/broadcasts` → `{id, sent, failed}`; errors: 400/403/429.
- `PUT /api/v1/admin/menu/week` → `{week}`; errors: 400/403.
- `PUT /api/v1/admin/menu/{day}` → `{day, items[]}`; errors: 400/403.
- `POST /api/v1/admin/menu/photo` → multipart image upload → `{url}`; errors: 400/413/500.
- `POST /api/v1/admin/order-window` → `{enabled, weekStart}`; errors: 400/403.
- Health endpoints: `/healthz`, `/readyz`.

## Data Model Targets
- `users`: id (uuid/int), telegram_id, roles, address, phone, created_at, updated_at.
- `orders`: id (UUID/ULID), public_id (BLB-… format), user_id FK, day (enum Mon-Fri), count (1-4), status (`new`, `cancelled_by_user`, `cancelled`, future statuses TBD), menu_snapshot JSON, address_snapshot, phone_snapshot, delivery_week_start (date), next_week (bool), created_at, updated_at.
- `menu_weeks`: id, week_start (date, unique), title, is_published, created_at, updated_at.
- `menu_items`: id, menu_week_id FK, day (enum), position, title, description, photo_url.
- `order_windows`: id, week_start (date), enabled (bool), created_at, updated_at.
- `broadcasts`: id, author_id, channels[], html_body, status, sent_at, created_at.
- Index guidance: orders by (delivery_week_start, status), (user_id, day, delivery_week_start); menu_items by (menu_week_id, day, position).

## Domain Rules Extracted from `bot.py`
- Days limited to Mon–Fri via `DAY_TO_INDEX`; invalid day → rejection.
- Order window: `_load_order_window()` toggles `next_week_enabled` with `week_start`; `_is_day_available_for_order()` enforces:
  - Past days blocked unless next week window active.
  - Same-day orders cut off at `ORDER_CUTOFF_HOUR = 10` (10:00 local).
  - When next week window expires, flag auto-resets.
- Duplicate prevention: `find_user_order_same_day(user_id, day, week_start)` finds active (non-cancelled) orders in same week, returning latest order; UI asks to overwrite or adjust.
- Anti-spam: selecting count/order limited to once every 10 seconds (`last_order_ts`).
- Order ID format: `BLB-{timestamp base36}-{uid tail base36}-{random base36}` via `make_order_id`.
- Order persistence: JSON storage; `save_order` writes snapshot with `status="new"`; status transitions via `set_order_status` to `cancelled_by_user` (self) or `cancelled` (admin).
- Profiles: `users.json` stores address + phone; `address_phone` step saves contact via Telegram contact or text; requires address before confirmation.
- Menu handling: `menu.json` includes `week` label and `menu{day: items[]}`; admin flows allow CRUD on menu text and `Menu.jpeg` + per-day photos `DishPhotos/*`.
- Broadcasts: `/sms <html>` sends HTML message to all users except admin; recipients aggregated from users + orders via `get_broadcast_recipients`.
- Reports: admin weekly summaries aggregate counts per day, separate cancelled orders.
- Pricing: constant `PRICE_LARI = 15`; total = count * price (no currency conversion yet).

## Bot ↔ Web UI Mapping
- `/start`, `🔄 В начало` → `/` (landing/onboarding with CTA to view menu/order).
- `Показать меню на неделю` → `/menu` (tabbed week/day view with gallery from menu items).
- `Заказать обед` dialogue → `/order/new` wizard with steps: select day & quantity → address/contact → confirmation.
- Duplicate order inline resolution → modal/dialog in `/order/new` or `/orders/{id}` with options to overwrite or keep.
- `Мои заказы` & inline change/cancel → `/account/orders` list + `/orders/{id}` detail; actions for update/cancel using REST endpoints.
- Admin “Показать заказы на эту неделю” → `/admin/reports` (filters by day/week, CSV export).
- Admin menu management commands → `/admin/menu` (week CRUD, day item editing, photo upload, order window toggle).
- `/order <ID>` → `/orders/{id}` (requires owner/admin). `/cancel <ID>` → `/orders/{id}` cancel action.
- `/sms` broadcasts → `/admin/broadcast` form with rate limiting and segmentation (future).
- Operator contacts button → contact modal accessible from `/` and header.

## Open Implementation TODOs
- Choose specific UI component library (Chakra vs MUI) consistent across frontend. (TODO: select per team alignment.)
- Define exact Redis key schema for sessions and rate limiting. (TODO).
- Clarify notification channels (email/SMS/push) for broadcast & order confirmations. (TODO; default to log stub).
- Determine integration with Telegram OAuth vs email/password; roadmap mentions magic-link—pending decision. (TODO with placeholder auth provider).

