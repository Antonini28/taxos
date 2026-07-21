# TaxOS task runner — CI runs these same targets (Phase 6 doc 01 §3)

set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

# Start local stack (detached) and wait for health
up:
    docker compose up -d --wait
    uv run alembic upgrade head

down:
    docker compose down

# Fast unit tests (no containers)
test:
    uv run pytest -q

# Lint + types — exactly what CI runs
lint:
    uv run ruff check .
    uv run ruff format --check .

fmt:
    uv run ruff check --fix .
    uv run ruff format .

# Run the API against the compose stack
api:
    uv run uvicorn taxos_api.main:app --reload --port 8000

# Run the frontend dev server
web:
    npm run dev --prefix apps/frontend

# Seed the demo tenant with its documented findings
seed:
    uv run python tools/seed/seed.py --reset

# One command from empty to a platform worth showing
demo:
    uv run python tools/seed/demo.py

# ...and through the approval gate as well
demo-full:
    uv run python tools/seed/demo.py --approve

# Regenerate product screenshots (both themes) — requires the app running
assets:
    uv run python tools/assets/capture.py
