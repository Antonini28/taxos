# 01 — Repository Structure & Tooling

## 1. Monorepo layout

One repository (Phase 12 packaging target). Python workspace managed with **uv** (2026 standard: lockfile speed, workspace support, replaces pip/poetry/venv juggling).

```
taxos/
├── apps/
│   ├── api/                    # taxos-api entrypoint (FastAPI app assembly only — no logic)
│   │   ├── main.py             # app factory, router mounting, middleware stack
│   │   └── Dockerfile
│   ├── workers/                # taxos-workers entrypoint (Celery app + task registration)
│   ├── agents/                 # taxos-agents entrypoint (LangGraph runtime, tool clients)
│   └── frontend/               # Next.js app (Phase 7)
├── src/
│   ├── taxos_core/             # THE domain codebase (imported by api + workers)
│   │   ├── identity/           #   each module: see module template (doc 02 §2)
│   │   ├── masterdata/
│   │   ├── ingestion/
│   │   ├── compliance/         #   incl. engine/ (pure) + packs/ (loader, verification)
│   │   ├── workflow/
│   │   ├── risk/
│   │   ├── reporting/
│   │   ├── audit/
│   │   └── shared/             #   authz, persistence (UoW), events (outbox), telemetry, config
│   ├── taxos_contracts/        # Pydantic contracts: API schemas, events, envelopes, tool I/O
│   │   └── ...                 #   imported by EVERYTHING incl. agents & frontend codegen; deps: pydantic only
│   ├── taxos_agents/           # agent graphs, registry, prompts/, tool clients (LLM deps live here ONLY)
│   └── taxos_ml/               # detectors, feature views, training pipelines, registry client
├── packs/                      # jurisdiction content packs (source form, pre-signing)
│   └── uk-vat/
├── evals/                      # golden sets + eval harness (docs/ai/05)
├── migrations/                 # single Alembic history for taxos_core
├── infra/                      # Terraform roots + modules (Phase 8)
├── docs/                       # phases 1–5 output + runbooks/
├── tests/                      # mirrors src/ (unit) + integration/ + contract/
├── tools/                      # dev CLI (seed, dr-restore, pack-sign), lint plugins
├── docker-compose.yml          # local stack (doc 07)
├── pyproject.toml              # uv workspace root
├── justfile                    # task runner (see §3)
└── .github/workflows/          # CI (pr.yml, main.yml, nightly.yml — Phase 2 doc 08 §3)
```

Layout rationale: **entrypoints are thin** (`apps/*` contain assembly, never logic — the same `taxos_core` serves API and workers, which is what makes "one mutation path" possible); **contracts are a leaf package** (pydantic-only deps so the frontend type-generation and the agents service consume them without dragging the domain in); **agents' isolation is directory-visible** (the AP-2 dependency guard is a one-line check on `taxos_core`/`taxos_ml` lockfile groups).

## 2. Quality gates (configs live at repo root; CI runs them verbatim)

| Gate | Tool & config | Failure mode it prevents |
|---|---|---|
| Lint + format | **ruff** (lint incl. `flake8-bandit` security rules + format) — one tool, one config | Style debates; known-dangerous patterns |
| Types | **mypy --strict** per package (`taxos_contracts` first — contracts must be airtight) | Boundary drift, None-blindness |
| Module boundaries | **import-linter**: layered contract (Phase 2 doc 03 §1 dependency rule transcribed) + independence contract between domain modules | ADR-001 erosion |
| LLM dependency guard | CI step: `uv export --package taxos_core \| grep -E 'openai\|langchain\|anthropic'` → fail if hit | AP-2 violation |
| Float-in-compliance ban | ruff per-directory rule (custom plugin in `tools/lint/`): no `float` literals/annotations under `compliance/engine/` | ADR-005 arithmetic drift |
| Raw-commit ban | ruff plugin: `session.commit()` allowed only in `shared/persistence/` | Unaudited mutations |
| Secrets | gitleaks (pre-commit + CI) | Credential leakage |
| Dependencies | `uv lock --check` + trivy scan + licence allow-list | Drift, CVEs, licence risk |

### import-linter excerpt (normative)

```ini
[importlinter]
root_package = taxos_core

[importlinter:contract:layers]
name = Module layering (ADR-001 / doc 03)
type = layers
layers =
    reporting
    risk | workflow
    compliance
    ingestion
    masterdata
    identity
    shared
# reporting depends only downward; nothing imports reporting

[importlinter:contract:internals]
name = No cross-module internals
type = forbidden
# modules may import siblings' `service` and `events` only — enforced by
# forbidding `.repository`/`.models` cross-imports (generated per module pair)
```

## 3. Task runner (`justfile`) — the developer API

```
just up            # compose stack up (detached) + migrate + seed
just api           # run taxos-api with reload against compose services
just test          # unit tests (fast, no containers)
just test-int      # integration tests (compose-backed)
just lint          # ruff + mypy + import-linter + guards (exactly what CI runs)
just migrate m=""  # alembic revision --autogenerate -m ... (+ guard, doc 03 §5)
just evals a=""    # run eval suite (optionally per agent)
just seed profile= # load synthetic dataset profile (doc 07)
```

Rule: **CI runs `just lint` and `just test*` — the same entry points developers run.** No CI-only incantations; "works locally, fails in CI" is a bug class we design out.

## 4. Versioning & branching

Trunk-based: short-lived branches → PR (required checks = doc 08 §3 PR pipeline) → squash to `main`; `main` is always deployable (staging auto-deploys from it). Releases are tags (`v0.x.y`, SemVer while pre-1.0) cut from `main`; images tagged with git SHA + release tag. Conventional Commits enforced (commitlint) — the changelog and Phase 12's "meaningful commits" requirement fall out for free.
