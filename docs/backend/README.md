# Phase 6 — Backend Engineering

**Product:** Enterprise Agentic Tax Operating System (TaxOS)
**Status:** Complete — awaiting stakeholder review
**Inputs:** Phase 2 (containers, modules, API design, data architecture, ADR-001..011), Phase 3 (agent runtime contracts), Phase 5 (ML pipelines)
**Last updated:** 2026-07-20

## Purpose

This phase converts architecture into **enforceable implementation standards**: the repository skeleton, the reference implementations of the load-bearing patterns (audited unit-of-work, RLS sessions, outbox, idempotent tasks, problem+json errors), and the CI gates that make the Phase 2 rules mechanical rather than aspirational. Code snippets in these documents are **normative** — the build copies them, deviations need a PR argument.

## Document map

| # | Document | Covers |
|---|----------|--------|
| 01 | [Repository Structure & Tooling](01-repository-structure.md) | Monorepo layout, packaging (uv), lint/type/import gates, config files |
| 02 | [Application Architecture](02-application-architecture.md) | FastAPI composition, module template, DI, settings, middleware, error handling |
| 03 | [Persistence](03-persistence.md) | SQLAlchemy 2 patterns, the audited UoW (audit + outbox + mutation in one transaction), RLS sessions, Alembic discipline |
| 04 | [Async & Tasks](04-async-tasks.md) | Celery patterns, idempotency, outbox relay, beat schedules, WebSocket bridge |
| 05 | [API Implementation Standards](05-api-standards.md) | Router conventions, pagination/ETag/idempotency implementations, OpenAPI pipeline, auth dependencies |
| 06 | [Testing Strategy](06-testing.md) | Test pyramid, fixtures, factories, invariant tests, contract tests, coverage gates |
| 07 | [Local Development](07-local-dev.md) | docker compose, task runner, seeding, dev identity, inner-loop ergonomics |

## Standing rules (the short version every PR is reviewed against)

1. **One mutation path:** all business writes go through the audited UoW (doc 03). A raw `session.commit()` outside it is a review reject; CI greps for it.
2. **Types are the contract:** `mypy --strict` on `src/`; Pydantic models at every boundary (API, events, tasks, tool gateway); no `Any` without a `# justified:` comment.
3. **Module boundaries are law:** import-linter contracts (doc 01) fail the build on cross-module internals imports (ADR-001).
4. **No LLM SDKs outside `taxos-agents`** — dependency-guard CI job (AP-2).
5. **Decimal for money, always;** floats in the compliance module are lint-banned (ADR-005).
6. **Every endpoint:** authZ dependency, problem+json errors, OpenAPI-complete annotations, tests. No exceptions for "internal" endpoints.
7. **Idempotency by default:** POST handlers accept `Idempotency-Key`; tasks and event consumers are replay-safe (doc 04).
