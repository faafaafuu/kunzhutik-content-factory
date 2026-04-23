COMPOSE=docker compose

.PHONY: up down logs migrate seed lint

up:
	$(COMPOSE) up --build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

migrate:
	$(COMPOSE) exec api alembic upgrade head

seed:
	curl -X POST http://localhost:8000/api/v1/bootstrap/default

lint:
	python3 -m compileall services packages

