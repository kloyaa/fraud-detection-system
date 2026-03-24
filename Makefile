.PHONY: help dev test lint typecheck clean install migrate docker-up docker-down docker-logs docker-build docker-prod

help:
	@echo "Risk Assessment System (RAS) Backend"
	@echo "===================================="
	@echo ""
	@echo "Docker (Recommended):"
	@echo "  make docker-up              Start full stack (app + postgres + redis) with auto-reload"
	@echo "  make docker-down            Stop all services"
	@echo "  make docker-logs            Follow app logs"
	@echo "  make docker-build           Build Docker image"
	@echo "  make docker-test            Run tests inside Docker"
	@echo "  make docker-prod            Start production stack (requires .env.prod)"
	@echo ""
	@echo "Development (without Docker):"
	@echo "  make dev              Run FastAPI dev server (reload on code change)"
	@echo "  make install          Install dependencies + pre-commit hooks"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run all tests (pytest)"
	@echo "  make test-unit        Run unit tests only"
	@echo "  make test-integration Run integration tests"
	@echo "  make test-cov         Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint             Run Ruff linter + formatter"
	@echo "  make typecheck        Run mypy strict type checking"
	@echo "  make format           Auto-format code with Ruff"
	@echo ""
	@echo "Database:"
	@echo "  make migrate          Run Alembic migrations to latest"
	@echo "  make migrate-down     Rollback last migration"
	@echo "  make migrate-new NAME Create new migration (e.g. 'make migrate-new add_users_table')"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            Remove __pycache__, .pytest_cache, .mypy_cache"
	@echo "  make clean-all        Remove all generated files + venv"

# Docker Commands
docker-up:
	docker-compose up -d
	@echo "Stack started. Access app at http://localhost:8000"
	@echo "View logs: docker-compose logs -f app"

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f app

docker-build:
	docker build -t ras:latest .

docker-test:
	docker-compose exec app pytest -xvs

docker-prod:
	@if [ ! -f .env.prod ]; then \
		echo "Error: .env.prod not found. Copy from .env.prod.example and configure."; \
		exit 1; \
	fi
	docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d
	@echo "Production stack started"
	@echo "Check health: docker exec ras_app_prod curl http://localhost:8000/v1/health"

# Development Commands
dev:
	python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

install:
	pip install -r requirements.txt
	pre-commit install

test:
	pytest -xvs

test-unit:
	pytest -xvs -m unit

test-integration:
	pytest -xvs -m integration

test-cov:
	pytest --cov=app --cov-report=html --cov-report=term-missing

lint:
	ruff check app tests --fix
	ruff format app tests

typecheck:
	mypy app

format:
	ruff format app tests

migrate:
	alembic upgrade head

migrate-down:
	alembic downgrade -1

migrate-show:
	alembic current

migrate-new:
	@if [ -z "$(NAME)" ]; then echo "Usage: make migrate-new NAME=description"; exit 1; fi
	alembic revision --autogenerate -m "$(NAME)"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name *.egg-info -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage

clean-all: clean
	rm -rf venv/
	find . -name "*.pyc" -delete
