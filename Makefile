# developerOS — local development convenience targets.
#
# Run `make help` for the full list.
#
# Defaults:
#   - Backend runs from server/.venv (CLAUDE.md: system Python is python3 only;
#     venv provides the `python` alias).
#   - Postgres + Redis come from docker-compose.yml (the dev compose file).
#   - Client + Console are SvelteKit dev servers (Vite defaults: 5173 and 5174).
#
# Override anything via env vars on the command line, e.g.:
#   make backend PORT=8001
#   make client PORT=5180

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

# ---------------------------------------------------------------------------
# Paths & ports
# ---------------------------------------------------------------------------

SERVER_DIR    := server
CLIENT_DIR    := client
CONSOLE_DIR   := console
VENV          := $(SERVER_DIR)/.venv
PY            := $(VENV)/bin/python
PIP           := $(VENV)/bin/pip
MANAGE        := $(PY) manage.py

BACKEND_PORT  ?= 8000
CLIENT_PORT   ?= 5173
CONSOLE_PORT  ?= 5174

COMPOSE       := docker compose
COMPOSE_FILE  ?= docker-compose.yml

.DEFAULT_GOAL := help
.PHONY: help install install-server install-client install-console \
        venv up down restart logs ps \
        db-up db-down \
        backend migrate makemigrations shell superuser celery beat \
        client console \
        dev dev-stop \
        test test-server test-calendar test-workspace \
        check check-client check-console \
        format lint \
        clean clean-pyc clean-node

# ---------------------------------------------------------------------------
# Help (default target) — keeps target descriptions inline via `## comments`
# ---------------------------------------------------------------------------

help: ## Show this help.
	@printf "\033[1mdeveloperOS — make targets\033[0m\n\n"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / { printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@printf "\nCommon flows:\n"
	@printf "  \033[33mFirst-time setup:\033[0m   make install && make db-up && make migrate\n"
	@printf "  \033[33mDaily dev:\033[0m          make dev      # db+redis docker, backend+client+console local\n"
	@printf "  \033[33mFull stack docker:\033[0m  make up\n"

# ---------------------------------------------------------------------------
# Install dependencies
# ---------------------------------------------------------------------------

venv: ## Create the Python virtualenv at server/.venv.
	@test -d $(VENV) || python3 -m venv $(VENV)
	@$(PIP) install --upgrade pip --quiet
	@echo "venv ready at $(VENV)"

install-server: venv ## Install Python deps into server/.venv.
	@cd $(SERVER_DIR) && ../$(PIP) install -r requirements.txt

install-client: ## Install client npm deps.
	@cd $(CLIENT_DIR) && npm install

install-console: ## Install console npm deps.
	@cd $(CONSOLE_DIR) && npm install

install: install-server install-client install-console ## Install everything.

# ---------------------------------------------------------------------------
# Docker compose: full stack
# ---------------------------------------------------------------------------

up: ## Start the full docker stack (db, redis, server, celery, nginx).
	@$(COMPOSE) -f $(COMPOSE_FILE) up -d

down: ## Stop the full docker stack.
	@$(COMPOSE) -f $(COMPOSE_FILE) down

restart: down up ## Restart the full docker stack.

logs: ## Tail logs from all services.
	@$(COMPOSE) -f $(COMPOSE_FILE) logs -f --tail=100

ps: ## Show running services.
	@$(COMPOSE) -f $(COMPOSE_FILE) ps

# ---------------------------------------------------------------------------
# Docker compose: db + redis only (for local backend dev)
# ---------------------------------------------------------------------------

db-up: ## Start ONLY db + redis (so you can run backend locally).
	@$(COMPOSE) -f $(COMPOSE_FILE) up -d db redis
	@echo "Waiting for postgres + redis to be healthy..."
	@until $(COMPOSE) -f $(COMPOSE_FILE) exec -T db pg_isready -U postgres >/dev/null 2>&1; do sleep 1; done
	@echo "✓ db ready"
	@until $(COMPOSE) -f $(COMPOSE_FILE) exec -T redis redis-cli ping >/dev/null 2>&1; do sleep 1; done
	@echo "✓ redis ready"

db-down: ## Stop db + redis.
	@$(COMPOSE) -f $(COMPOSE_FILE) stop db redis

# ---------------------------------------------------------------------------
# Backend — run from local venv against docker db + redis
# ---------------------------------------------------------------------------

backend: ## Run Django dev server (localhost:$(BACKEND_PORT)) against docker db.
	@cd $(SERVER_DIR) && ../$(PY) manage.py runserver $(BACKEND_PORT)

migrate: ## Apply pending migrations.
	@cd $(SERVER_DIR) && ../$(PY) manage.py migrate

makemigrations: ## Generate migrations for changed models.
	@cd $(SERVER_DIR) && ../$(PY) manage.py makemigrations

shell: ## Open Django shell_plus (or shell if shell_plus isn't installed).
	@cd $(SERVER_DIR) && (../$(PY) manage.py shell_plus 2>/dev/null || ../$(PY) manage.py shell)

superuser: ## Create a Django superuser.
	@cd $(SERVER_DIR) && ../$(PY) manage.py createsuperuser

celery: ## Start a celery worker locally.
	@cd $(SERVER_DIR) && ../$(VENV)/bin/celery -A config worker -l info

beat: ## Start celery beat (scheduled tasks).
	@cd $(SERVER_DIR) && ../$(VENV)/bin/celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

# ---------------------------------------------------------------------------
# Frontends
# ---------------------------------------------------------------------------

client: ## Run client SvelteKit dev server on $(CLIENT_PORT).
	@cd $(CLIENT_DIR) && npm run dev -- --port $(CLIENT_PORT)

console: ## Run console SvelteKit dev server on $(CONSOLE_PORT).
	@cd $(CONSOLE_DIR) && npm run dev -- --port $(CONSOLE_PORT)

# ---------------------------------------------------------------------------
# dev — one-command local dev spaces.
# Starts db+redis (docker), then backend + client + console (local).
# Ctrl-C cleans up the local processes; db+redis keep running.
# ---------------------------------------------------------------------------

PIDFILE_DIR := .make-pids

dev: db-up ## Start db+redis (docker) + backend + client + console (local).
	@mkdir -p $(PIDFILE_DIR)
	@printf "\n\033[1mStarting dev processes...\033[0m\n"
	@printf "  Backend:  http://localhost:$(BACKEND_PORT)\n"
	@printf "  Client:   http://localhost:$(CLIENT_PORT)\n"
	@printf "  Console:  http://localhost:$(CONSOLE_PORT)\n\n"
	@printf "Logs interleave below. Ctrl-C stops all local processes (db+redis stay up; run \033[36mmake db-down\033[0m to stop them).\n\n"
	@trap 'echo; echo "Stopping..."; kill $$(cat $(PIDFILE_DIR)/*.pid 2>/dev/null) 2>/dev/null; rm -rf $(PIDFILE_DIR); echo "Stopped. db+redis still running (make db-down to stop)."; exit 0' INT TERM; \
	(cd $(SERVER_DIR) && ../$(PY) manage.py runserver $(BACKEND_PORT) 2>&1 | sed 's/^/[backend] /') & echo $$! > $(PIDFILE_DIR)/backend.pid; \
	(cd $(CLIENT_DIR) && npm run dev -- --port $(CLIENT_PORT) 2>&1 | sed 's/^/[client]  /') & echo $$! > $(PIDFILE_DIR)/client.pid; \
	(cd $(CONSOLE_DIR) && npm run dev -- --port $(CONSOLE_PORT) 2>&1 | sed 's/^/[console] /') & echo $$! > $(PIDFILE_DIR)/console.pid; \
	wait

dev-stop: ## Kill any lingering dev processes (use if Ctrl-C didn't clean up).
	@if [ -d $(PIDFILE_DIR) ]; then \
		for f in $(PIDFILE_DIR)/*.pid; do \
			[ -f "$$f" ] && kill $$(cat "$$f") 2>/dev/null || true; \
		done; \
		rm -rf $(PIDFILE_DIR); \
		echo "Cleaned up dev pids."; \
	else \
		echo "No dev processes tracked."; \
	fi

# ---------------------------------------------------------------------------
# Testing & checks
# ---------------------------------------------------------------------------

test: test-server check-client check-console ## Run server tests + client/console type-checks.

test-server: ## Run all server tests (uses --keepdb for speed).
	@cd $(SERVER_DIR) && ../$(PY) manage.py test --keepdb

test-calendar: ## Run only apps.calendar tests.
	@cd $(SERVER_DIR) && ../$(PY) manage.py test apps.calendar --keepdb

test-workspace: ## Run only apps.workspace tests.
	@cd $(SERVER_DIR) && ../$(PY) manage.py test apps.workspace --keepdb

check: check-client check-console ## svelte-check both frontends.

check-client: ## Type-check the client app.
	@cd $(CLIENT_DIR) && npm run check

check-console: ## Type-check the console app.
	@cd $(CONSOLE_DIR) && npm run check

# ---------------------------------------------------------------------------
# UAT — end-to-end browser tests (Playwright)
# ---------------------------------------------------------------------------
# `make uat` assumes `make dev` is already running. It will:
#   1. run seed_test_org via Django to mint a JWT for a fixed test user
#   2. write a Playwright storageState so every spec starts logged in
#   3. run the Playwright suite (chromium by default)

E2E_DIR := e2e

.PHONY: uat uat-install uat-headed uat-codegen uat-report uat-seed

uat-install: ## One-time: install Playwright + browser binaries.
	@cd $(E2E_DIR) && npm install
	@cd $(E2E_DIR) && npx playwright install --with-deps chromium

uat-seed: ## Just (re)seed the test org + mint a fresh JWT.
	@cd $(SERVER_DIR) && ../$(PY) manage.py seed_test_org --output $(abspath $(E2E_DIR))/.auth/credentials.json

uat: ## Run the Playwright UAT suite headless.
	@cd $(E2E_DIR) && npm test

uat-headed: ## Run the UAT suite with a visible browser (debugging).
	@cd $(E2E_DIR) && npm run test:headed

uat-codegen: ## Record a new flow by clicking through the app.
	@cd $(E2E_DIR) && npm run codegen

uat-report: ## Open the last HTML report.
	@cd $(E2E_DIR) && npm run report

# ---------------------------------------------------------------------------
# Housekeeping
# ---------------------------------------------------------------------------

clean: clean-pyc ## Remove caches and __pycache__.

clean-pyc: ## Delete Python __pycache__ and .pyc files.
	@find . -type d -name __pycache__ -prune -exec rm -rf {} +
	@find . -type f -name '*.pyc' -delete
	@echo "Python caches cleared."

clean-node: ## Delete node_modules in client + console.
	@rm -rf $(CLIENT_DIR)/node_modules $(CONSOLE_DIR)/node_modules
	@echo "node_modules removed."
