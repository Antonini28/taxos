# TaxOS task runner — CI runs these same targets (Phase 6 doc 01 §3)

set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

# Start local stack (detached) and wait for health
up:
    docker compose up -d --wait

down:
    docker compose down

# Fast unit tests (no containers)
test:
    uv run pytest -q

# Lint + types — exactly what CI runs
lint:
    uv run ruff check .
    uv run ruff format --check .
    uv run mypy

# Run the API with reload against the compose stack
api:
    uv run uvicorn taxos_api.main:app --reload --port 8000

fmt:
    uv run ruff check --fix .
    uv run ruff format .
