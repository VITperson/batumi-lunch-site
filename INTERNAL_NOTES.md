# Internal Notes – Batumi Lunch Web Migration

## Stack & Architecture (from `roadmap.md`)
- Frontend: Next.js (React) SPA with SSR support; routes: `/`, `/menu`, `/order/new`, `/account/orders`, `/orders/{id}`, `/admin`, `/admin/menu`, `/admin/reports`, `/admin/broadcast`, `/login`.
- Backend: FastAPI exposing REST API described in roadmap (`/menu/week`, `/orders`, `/orders/{id}`, `/orders/{id}/cancel`, `/orders?mine=1`, `/admin/*`).
- Persistence: PostgreSQL tables `users`, `orders`, `menu_weeks`, `menu_items`, `order_windows`, `broadcasts`; required indexes on `delivery_date`, `status`, `user_id`.
- Cache/session: Redis for session storage, rate limiting (`POST /orders`, `/admin/broadcasts`).
- Storage: S3-compatible bucket (MinIO locally) for menu/media uploads.
- Async work: Celery/RQ worker tier to handle broadcasts/notifications.
- Observability: structured JSON logging, Prometheus metrics, Sentry, `/healthz`, `/readyz` endpoints.

## Domain Entities & Fields (from `bot.py`)
- `User`: `user_id`, `address` (free-text), `phone` (raw string from Telegram contact), optional `username`.
- `Order`: `order_id` (format `BLB-<ts36>-<uid36>-<rnd>`), `user_id`, `username`, `day`, `count`, `menu` (comma-joined string), `status` (`new`, `cancelled`, `cancelled_by_user`), `created_at`, `updated_at`, `delivery_week_start` (ISO date string), `next_week` (bool), `address`, `phone`.
- `Menu`: `week` label plus `menu[day]` list of dish strings; optional day photo map.
- `Order window`: `next_week_enabled` flag with `week_start` ISO date; governs ability to book next week deliveries.
- `Broadcast recipients`: union of all `user_id`s seen in users/orders JSON, excluding admin.

## Core Business Rules
- Order window: `_is_day_available_for_order(day)` disallows past days; same-day orders close after `ORDER_CUTOFF_HOUR=10`. If `next_week_enabled` and week start in future, selections target next week; otherwise stored against current week start (Monday).
- Order count: only 1–4 portions accepted (`select_count`), with textual and numeric aliases.
- Anti-spam: users must wait 10 seconds between order submissions (`context.user_data['last_order_ts']`).
- Duplicate detection: `find_user_order_same_day(user_id, day, week_start)` checks active (non cancelled) orders for selected week; user can either cancel existing (`status=cancelled_by_user`) or merge counts (sums quantities, persists to existing order, notifies admin).
- Profile persistence: `users.json` stores address/phone; `ensure_user_registered` guarantees entry; address is required before confirmation, phone optional but encouraged (button to send contact).
- Confirmation: order saved only after user chooses “Подтверждаю”. Admin notified with detailed HTML message; user receives summary + action buttons.
- Order modification: owner/admin may adjust quantity while `status=='new'`; updates persisted with new `updated_at` and admin notification.
- Cancellation: owner cancels via command/callback yielding `cancelled_by_user`; admin cancellation uses `cancelled`.
- Reporting: weekly/day reports aggregate counts, totals, include cancelled orders separately, display Telegram deep links.
- Menu management: admin can set week title, add/edit/remove dishes per day, upload photo, toggle next-week orders (sets `next_week_enabled` and computes `_next_week_start()`).

## Validation & Data Handling
- Address input prompted with guideline text; stored verbatim, minimal validation (non-empty string).
- Phone numbers preserved as provided; sanitized copy for tel-link in operator contacts via `re.sub(r"[^\d+]", "", phone)`.
- Menus validated on load to ensure `{'week': str, 'menu': dict}`.
- JSON saves use atomic write via temp file + `os.replace` for idempotency.
- Duplicate week orders ensure week context via `delivery_week_start`; fallback to timestamp range of current week if missing.

## Conversation → Web Mapping
- `/start`, `🔄 В начало` → landing `/` with onboarding CTA.
- `Показать меню на неделю` → `/menu` (tabbed daily view with optional images).
- `Заказать обед` → `/order/new` multi-step wizard (day/count → address/contact → confirm).
- `Мои заказы` → `/account/orders` list with inline actions (change/cancel).
- `/order <ID>` + inline keyboards → `/orders/{id}` detail view (with admin/customer access control).
- `/cancel <ID>` + callbacks → action on `/orders/{id}` (cancel endpoint/button).
- `Показать заказы на эту неделю` → `/admin/reports` (daily/weekly aggregates, cancel audit trail).
- `Управление меню` → `/admin/menu` (week label, CRUD dishes, photo upload, next-week toggle).
- `/sms` → `/admin/broadcast` (HTML broadcast form with rate limiting).
- “Связаться с человеком” → contact modal with operator handle/phone/Instagram.

## Open UX / Feature Notes
- Existing UX already implies saved addresses, ability to plan next week, highlight duplicates, show confirmation gif.
- Roadmap adds enhancements: calendar picker, optional online payments, notifications (email/SMS/push), admin KPI dashboard; mark where TODOs or safe stubs required.

