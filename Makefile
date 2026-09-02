.PHONY: install dev test lint format typecheck up down ingest smoke

install:
	python -m pip install -e ".[dev]"

dev:
	uvicorn app.main:app --reload --port 8000

test:
	pytest -q

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy app

up:
	docker compose up -d --build

down:
	docker compose down

ingest:
	python scripts/ingest.py

smoke:
	python scripts/smoke_test.py
