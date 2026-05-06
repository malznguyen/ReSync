COMPOSE ?= docker compose
SERVICE ?= postgres

.PHONY: up down logs shell migrate seed-dev health-check

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down -v --remove-orphans

logs:
	$(COMPOSE) logs -f

shell:
	$(COMPOSE) exec $(SERVICE) sh

migrate:
	$(COMPOSE) run --rm storage_tools sh -lc "python -m pip install -r api/requirements.txt && python -m alembic upgrade head"

seed-dev:
	$(COMPOSE) run --rm storage_tools sh -lc "python -m pip install -r api/requirements.txt && python scripts/seed_dev.py"

health-check:
	$(COMPOSE) run --rm storage_tools sh -lc "python -m pip install -r api/requirements.txt && python scripts/health_check.py"
