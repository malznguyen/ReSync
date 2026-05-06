COMPOSE ?= docker compose
SERVICE ?= postgres

.PHONY: up down logs shell migrate

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down -v --remove-orphans

logs:
	$(COMPOSE) logs -f

shell:
	$(COMPOSE) exec $(SERVICE) sh

migrate:
	$(COMPOSE) exec postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -f /docker-entrypoint-initdb.d/001-init.sql'
