.PHONY: dev install test

install:
	uv pip install -e ".[dev]"

dev:
	uvicorn app.main:app --reload --port 8000

test:
	pytest -q
