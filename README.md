# Batumi Lunch Web Platform

> Migration of the Batumi Lunch Telegram bot into a full web platform.

## Repository Layout
- `backend/` — FastAPI service, domain logic, migrations, tests.
- `frontend/` — Next.js application with user & admin flows.
- `scripts/` — Data migration and seed utilities.
- `deploy/` — Dockerfiles, compose stack, Alembic configuration.

## Getting Started
1. Copy `.env.sample` to `.env` (or `.env.local`) and adjust secrets (never commit real secrets).
2. Install dependencies:
   ```bash
   make install
   ```
3. Run database migrations and seed data:
   ```bash
   make migrate
   make seed
   ```
4. Launch services:
   ```bash
   make serve-api
   make serve-web
   ```

## Makefile Targets
See `Makefile` for available commands (`install`, `migrate`, `seed`, `serve-api`, `serve-web`, `test`, `lint`, `up`, `down`, `format`, `generate-openapi`).

## Roadmap Alignment
Implementation follows `roadmap.md`. Internal design references are tracked in `INTERNAL_NOTES.md`. Pending questions will be collected in `OPEN_QUESTIONS.md`.
