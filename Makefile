.PHONY: install lint format typecheck test run-api run-worker run-web \
       db-up db-down migrate docker-up docker-down clean

# ---------------------------------------------------------------------------
# Development setup
# ---------------------------------------------------------------------------
install:
	uv sync --all-packages

# ---------------------------------------------------------------------------
# Code quality
# ---------------------------------------------------------------------------
lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .

typecheck:
	uv run mypy .

# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------
test:
	uv run pytest

# ---------------------------------------------------------------------------
# Run services locally
# ---------------------------------------------------------------------------
run-api:
	uv run uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload

run-worker:
	uv run celery -A apps.worker.main worker --loglevel=info

run-web:
	cd apps/web && npm run dev

# ---------------------------------------------------------------------------
# Database helpers (requires docker compose)
# ---------------------------------------------------------------------------
db-up:
	docker compose up -d postgres redis

db-down:
	docker compose down postgres redis

migrate:
	uv run alembic upgrade head

# ---------------------------------------------------------------------------
# Docker Compose (full stack)
# ---------------------------------------------------------------------------
docker-up:
	docker compose up -d --build

docker-down:
	docker compose down -v

# ---------------------------------------------------------------------------
# Housekeeping
# ---------------------------------------------------------------------------
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".next" -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist build coverage .coverage
