.PHONY: install migrate seed serve-api serve-web test lint up down format generate-openapi

install:
	cd backend && poetry install
	npm install --prefix frontend

migrate:
	cd backend && poetry run alembic upgrade head

seed:
	cd backend && poetry run python ../scripts/seed_menu.py

serve-api:
	cd backend && poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

serve-web:
	npm run dev --prefix frontend

test:
	cd backend && poetry run pytest
	npm test --prefix frontend || true

lint:
	cd backend && poetry run ruff check app
	cd backend && poetry run mypy app
	npm run lint --prefix frontend

up:
	cd deploy && docker compose up -d --build

down:
	cd deploy && docker compose down

format:
	cd backend && poetry run ruff format app
	cd backend && poetry run black app
	npm run lint --prefix frontend -- --fix

generate-openapi:
	cd backend && poetry run python -m app.tools.generate_openapi
