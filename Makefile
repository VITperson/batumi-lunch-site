PYTHON ?= python3
PIP ?= $(PYTHON) -m pip
NPM ?= npm
DOCKER_COMPOSE ?= docker compose
ALEMBIC ?= alembic

.PHONY: install install-backend install-frontend migrate seed serve-api serve-web test lint up down fmt openapi

install: install-backend install-frontend

install-backend:
	$(PIP) install -e backend[dev]

install-frontend:
	cd frontend && $(NPM) install

migrate:
	cd backend && $(ALEMBIC) -c ../deploy/alembic.ini upgrade head

seed:
	$(PYTHON) scripts/seed_menu.py

serve-api:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

serve-web:
	cd frontend && $(NPM) run dev

test:
	cd backend && pytest

lint:
	cd backend && ruff check app && mypy app

fmt:
	cd backend && ruff format app

openapi:
	cd backend && python -m app.tools.generate_openapi

up:
	$(DOCKER_COMPOSE) -f deploy/docker-compose.yml up -d --build

down:
	$(DOCKER_COMPOSE) -f deploy/docker-compose.yml down -v
