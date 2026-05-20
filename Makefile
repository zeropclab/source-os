.PHONY: dev test lint migrate seed clean install

install:
	pip install -r requirements.txt -r requirements-dev.txt
	playwright install chromium

dev:
	docker compose up -d
	sleep 2
	uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

worker:
	rq worker --url redis://localhost:6379/0

scheduler:
	python -m apps.worker.scheduler

test:
	DATABASE_URL=postgresql+asyncpg://postgres:sourceos@localhost:5432/sourceos_test \
	REDIS_URL=redis://localhost:6379/1 \
	STORAGE_ROOT=/tmp/sourceos-test \
	pytest -v --cov --cov-report=term-missing

lint:
	ruff check .
	ruff format --check .
	mypy packages/ apps/ --ignore-missing-imports

fmt:
	ruff check --fix .
	ruff format .

migrate:
	alembic upgrade head

migrate-new:
	alembic revision --autogenerate -m "$(msg)"

seed:
	python infra/scripts/seed_sources.py

clean:
	docker compose down -v
	rm -rf data/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name *.egg-info -exec rm -rf {} + 2>/dev/null || true
