COMPOSE=docker compose

.PHONY: up down logs bot-logs ps migrate seed lint

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

bot-logs:
	$(COMPOSE) logs -f telegram-bot

ps:
	$(COMPOSE) ps

migrate:
	$(COMPOSE) exec api alembic upgrade head

seed:
	curl -X POST http://localhost:8000/api/v1/bootstrap/default

lint:
	python3 -m compileall services packages
