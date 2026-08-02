.PHONY: dev test lint format migrate install

install:
	uv sync --extra dev

dev:
	docker compose up -d
	uv run alembic upgrade head
	uv run uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000

test:
	uv run pytest -q

lint:
	uv run ruff check apps packages tests
	uv run ruff format --check apps packages tests

format:
	uv run ruff format apps packages tests

migrate:
	uv run alembic upgrade head
