# 06 — Testing Strategy (backend)

*Phase 10 owns the full test programme (load, security, E2E, AI evals in depth); this document fixes the backend patterns and gates the build ships with from day one.*

## 1. The pyramid, TaxOS-shaped

| Layer | Scope | Infra | Speed | Volume |
|---|---|---|---|---|
| Unit | Services (fake repos), policies, engine (property-based), pure functions | none | ms | thousands |
| Component | Repos + UoW + RLS against real Postgres; task idempotency against real Redis | compose (testcontainers-style ephemeral schemas) | 100ms | hundreds |
| Integration | API through HTTP (httpx ASGI client) with real DB; event flows producer→consumer | compose | s | ~100 |
| Contract | OpenAPI conformance (schemathesis), route-guard walk, POST-idempotency walk | compose | s | generated |
| Invariant | The architectural guarantees as executable tests (§3) | compose | s | ~20, precious |
| E2E / evals / load | Phase 10 | staging | min | scripted |

`just test` = unit only (inner loop, <30s); `just test-int` = component+integration+contract+invariant (PR gate).

## 2. Fixtures & factories

- **factory_boy** factories per aggregate with realistic defaults (UK VAT codes, GBP amounts as Decimals, valid entity scopes); a `scenario()` helper composes them into coherent states ("entity with validated Q2 batch and draft computation") — tests read like the domain.
- DB fixtures: one migrated template database per session; each test gets a fresh schema-copy (fast) with RLS active and a seeded tenant pair (`tenant_a`, `tenant_b`) — **two tenants in every DB fixture by default**, so cross-tenant assertions are always one line away.
- Engine fixtures: golden `vat-scenarios` (shared with evals — one source of truth for what correct looks like).
- Time: `freezegun`-style clock fixture injected via a `Clock` protocol (no naked `datetime.now()` in domain code — lint rule; deadline logic is untestable otherwise).

## 3. Invariant tests (the architecture, executable)

The suite that makes the ADRs true forever:

```
test_unaudited_mutation_cannot_commit        # UoW without audit draft raises (ADR-009)
test_state_audit_outbox_atomic               # induced crash pre-commit leaves no partial rows
test_audit_chain_verifies_and_detects_tamper # rewrite a payload → chain verification fails
test_rls_blocks_cross_tenant_read            # tenant_a session, tenant_b data: zero rows (ADR-006)
test_rls_blocks_cross_tenant_write
test_preparer_cannot_approve                 # SoD via API, 403 + audit row (US-402/501)
test_approval_voided_on_content_change       # hash binding (US-402)
test_engine_determinism                      # property-based: same inputs+pack ⇒ identical hash (FR-205)
test_engine_no_float_reaches_arithmetic
test_immutable_tables_reject_update          # DB-level guard fires even via raw SQL
test_tool_gateway_has_no_approval_surface    # route-table walk (ADR-012)
test_agent_service_db_role_has_no_business_grants
test_event_consumer_idempotent_on_replay     # same event twice ⇒ one effect
test_duplicate_batch_upload_rejected         # content-hash dedupe (US-201)
```

These are the tests a security reviewer or interviewer is shown first. They never get skipped, they run in the PR gate, and a change that breaks one is definitionally an architecture change requiring an ADR update.

## 4. Coverage & quality gates

- Coverage gate: **85% line + branch on `taxos_core`** (NFR-10), measured on unit+component; `compliance/engine/` and `shared/persistence/` held to **95%** (the code where bugs are incidents). Coverage is a floor, not a target — review still asks "is the *behaviour* tested".
- Mutation testing (mutmut) on `compliance/engine/` and `policies.py` files in the nightly pipeline — assertion-free tests die here.
- Flake policy: a flaky test is quarantined within 24h (marked, tracked, fixed or deleted within the sprint) — a red-when-fine suite trains people to ignore red.
- Every bugfix PR carries a regression test reproducing the bug first (reviewer checklist item).

## 5. What we deliberately do not test

Framework internals (FastAPI routing, SQLAlchemy SQL emission), third-party behaviour behind ports (the `Retriever` is contract-tested; pgvector itself is not our test surface), and LLM outputs in unit tests (that's the eval harness's job — docs/ai/05; unit tests use recorded/stub envelopes). Test effort goes where our logic lives.
