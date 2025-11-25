SHELL := /bin/sh

DC := docker compose
DC_FILE := docker-compose.yml
MIGRATION_SQL ?= docs/design/migration-0001.sql
DB_HOST ?= 127.0.0.1
DB_PORT ?= 3306
DB_USER ?= app
DB_PASS ?= app_password
DB_NAME ?= reservation

.PHONY: db-up db-down db-logs db-ps db-cli db-migrate dev-up

# Start MySQL in background
db-up:
	$(DC) -f $(DC_FILE) up -d db

# Start backend dev environment (backend + db)
dev-up:
	$(DC) -f $(DC_FILE) up -d backend db

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
