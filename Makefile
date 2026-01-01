SHELL := /bin/sh

DC := docker compose
DC_FILE := docker-compose.yml
MIGRATION_SQL ?= docs/design/migration-0001.sql
DB_HOST ?= 127.0.0.1
DB_PORT ?= 3306
DB_USER ?= app
DB_PASS ?= app_password
DB_NAME ?= reservation
SEED_SQL ?= backend/migrations/seed_dev.sql

.PHONY: db-up db-down db-logs db-ps db-cli db-migrate dev-up dev-all frontend-up frontend-logs seed-dev

# Start MySQL in background
db-up:
	$(DC) -f $(DC_FILE) up -d db

# Start backend dev environment (backend + db)
dev-up:
	$(DC) -f $(DC_FILE) up -d backend db

# Start backend+db+frontend dev environment
dev-all:
	$(DC) -f $(DC_FILE) up -d backend db frontend

# Start frontend only (expects backend/db already running)
frontend-up:
	$(DC) -f $(DC_FILE) up -d frontend

frontend-logs:
	$(DC) -f $(DC_FILE) logs -f frontend

# Stop and remove MySQL container
db-down:
	$(DC) -f $(DC_FILE) down

# Show DB logs
db-logs:
	$(DC) -f $(DC_FILE) logs -f db

# List containers
db-ps:
	$(DC) -f $(DC_FILE) ps

# MySQL CLI via container (interactive; requires TTY)
db-cli:
	$(DC) -f $(DC_FILE) exec -it db mysql -u$(DB_USER) -p$(DB_PASS) $(DB_NAME)

# Apply SQL migration file via container mysql
db-migrate:
	test -f "$(MIGRATION_SQL)" || (echo "missing migration file: $(MIGRATION_SQL)" && exit 1)
	cat $(MIGRATION_SQL) | $(DC) -f $(DC_FILE) exec -T db mysql -u$(DB_USER) -p$(DB_PASS) $(DB_NAME)

# Apply development seed data (idempotent)
seed-dev:
	test -f "$(SEED_SQL)" || (echo "missing seed file: $(SEED_SQL)" && exit 1)
	cat $(SEED_SQL) | $(DC) -f $(DC_FILE) exec -T db mysql -u$(DB_USER) -p$(DB_PASS) $(DB_NAME)
