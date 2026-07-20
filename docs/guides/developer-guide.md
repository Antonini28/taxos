# Developer Guide

Welcome. This guide gets you productive in a day; depth lives in the linked normative docs.

## Day one

1. **Environment:** `just up` (compose + migrate + seed) — [local dev](../backend/07-local-dev.md). Devcontainer available. Target: working stack < 5 min.
2. **Log in** at `localhost:3000` with a persona user (`daniel@dev` = preparer is the best first seat). Run `just demo` to watch the flagship flow once before reading any code.
3. **Orient:** read the [60-second architecture](../../README.md#the-60-second-architecture), then [module map](../architecture/03-component-architecture.md). Code layout mirrors it exactly ([repo structure](../backend/01-repository-structure.md)).
4. **First change:** pick a `good-first-issue`; the loop is `just test` (fast) → `just lint` → PR. CI runs the same commands.

## The five rules you must not learn the hard way

1. **All business writes go through `AuditedUnitOfWork`** — a bare `session.commit()` fails lint. [Why + pattern](../backend/03-persistence.md).
2. **Money is `Decimal`; floats are banned in the engine** (lint-enforced). Rounding happens only at pack-defined points.
3. **Module boundaries are CI-enforced** (import-linter). Need another module's data? Its service interface or a domain event — never its repo/models.
4. **No LLM SDKs outside `taxos_agents`** (CI guard). Agent capabilities are added as Tool Gateway endpoints + registry grants + contract types — [three artifacts, deliberately](../architecture/adr/ADR-012-agent-runtime-isolation.md).
5. **Every mutating endpoint:** authz dependency, problem+json, idempotency key, tests. The [route checklist](../backend/05-api-standards.md#6-auth--security-defaults-implementation-checklist-per-endpoint) is what review checks.

## Common tasks → where the pattern lives

| Task | Pattern |
|---|---|
| New endpoint | [API kit](../backend/05-api-standards.md) — copy an existing router; contract types in `taxos_contracts` first |
| New domain event | Contract in `taxos_contracts`, publish via UoW, consumer per [template](../backend/04-async-tasks.md#4-event-consumers), add to the [event catalogue](../architecture/05-eventing-and-async.md#3-event-catalogue-mvp) |
| Schema change | `just migrate` + [Alembic discipline](../backend/03-persistence.md#5-alembic-discipline) (expand→migrate→contract; RLS on new tables — the CI introspection test will catch you) |
| New agent tool | ADR-012 trio + grant config + [gateway specifics](../backend/05-api-standards.md#7-tool-gateway-specifics) |
| Prompt change | Edit versioned prompt + run `just evals a=<agent>` — [eval gates](../ai/05-agent-evaluation.md) block merge on regression |
| New rule-pack rule | Pack YAML + citation ref + golden scenario — [pack governance](../architecture/adr/ADR-005-rule-engine-content-packs.md) |
| New UI screen | [Page catalogue](../frontend/04-page-catalogue.md) spec first; composites from the [inventory](../frontend/01-design-system.md#6-component-inventory-shadcn-base--taxos-composites); states are not optional |
| New ML detector | [Cold-start ladder](../ml/01-ml-problem-map.md#2-the-cold-start-ladder-ml-3-made-operational) — rules first, model only with evidence |

## Conventions digest

Conventional Commits (enforced) · trunk-based, short branches, squash merges · PR template includes the reviewer checklists · mypy strict + TS strict, no unexplained `Any` · test naming `test_<behaviour>` not `test_<method>` · bugfix PRs lead with the failing regression test · docs updated in the same PR as behaviour changes.

## Getting unstuck

`just logs api` / `just psql` / `just dlq` for the stack · OTel traces locally via the `obs` compose profile (Grafana at :3001) · every error response carries a `trace_id` — paste it into the trace view · architecture questions: check the [ADR log](../architecture/README.md#adr-index) first; if the answer isn't there and the question is significant, the answer is a new ADR.
