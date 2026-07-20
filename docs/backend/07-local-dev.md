# 07 — Local Development Environment

## 1. docker compose stack

```yaml
services:
  postgres:        # 16-alpine; init scripts create app/migration/platform roles + RLS force
  redis:           # 7-alpine
  azurite:         # Blob emulation — same SDK code path as Azure (no "local mode" branches)
  dev-issuer:      # tiny OIDC provider (preconfigured users per persona P1–P6, one per role)
  mlflow:          # registry (Postgres-backed, artifacts→azurite)
  api:             # taxos-api, --reload, mounted src
  workers:         # celery worker -Q all queues, --autoreload (watchdog)
  scheduler:       # celery beat
  agents:          # taxos-agents; LLM: Azure OpenAI dev deployment OR local stub (see §3)
  frontend:        # Next.js dev server (Phase 7)
  otel-lgtm:       # optional profile "obs": Grafana/Tempo/Loki/Prom single container
```

`just up` = compose up + migrate + seed. Full cold start to working stack target: **< 5 minutes** — onboarding friction is a quality bar (this is also the reviewer/demo experience of the repo).

## 2. Seed data (`just seed profile=demo`)

The generator (`tools/seed/`) builds the synthetic estate deterministically from a seed value (reproducible bug reports):
- `minimal` — 1 tenant, 2 entities, 1 quarter, clean data (fast tests).
- `demo` — 1 tenant ("Meridian Group"), 5 UK entities, 6 quarters of AP/AR/GL with realistic volume, **seeded findings**: 14 near-duplicate invoices, VAT-code miscodings, an entity with chronic late payroll extracts, a period with a control-total break — the US-801/R1 exit-criteria demo runs on this profile, and every seeded finding is documented in `tools/seed/FINDINGS.md` so demos never fish.
- `multi` — 2 tenants for isolation demos/tests.
- `scale` — 1M+ transaction rows for NFR-06 local smoke (generator streams; no fixture files in git — data is always generated, never committed).

## 3. Working without cloud dependencies

| Dependency | Local strategy |
|---|---|
| Azure OpenAI | Dev deployment via env vars when available; otherwise **stub LLM mode**: recorded envelope fixtures for golden scenarios (agents replay known-good runs — demos and non-AI development don't burn tokens or require keys). Stub mode is visibly watermarked in the UI. |
| Entra ID | dev-issuer (§1) with persona users (`amara@dev` P1, `daniel@dev` P2, …) — logging in *as a persona* is also how UX flows get reviewed (Phase 7) |
| Key Vault / App Config | `.env` (gitignored) from committed `.env.example`; OpenFeature file provider for flags |
| Service Bus | Redis Streams adapter (ADR-003 — same `EventPublisher` port) |
| Blob | Azurite (same SDK) |

Principle: **local differs in providers, never in code paths** — every adapter swap happens behind a port that has a contract test, so "works locally" is evidence, not hope.

## 4. Inner-loop ergonomics

- `pre-commit`: ruff (fix+format), gitleaks, commitlint — fast hooks only (mypy/import-linter are `just lint`/CI; slow hooks get skipped by humans, then CI surprises them).
- `just logs [svc]`, `just psql`, `just redis-cli`, `just dlq`, `just chain-verify` (audit chain check against local DB) — the ops toolkit exists locally first; runbooks reference the same commands.
- VS Code devcontainer definition included (uv + extensions + compose attach) — one-click environment for reviewers.
- `just demo` — resets to `demo` profile, replays the flagship agent run in stub mode, opens the browser at the executive dashboard: the 3-minute portfolio demo is a build target, not an aspiration.
