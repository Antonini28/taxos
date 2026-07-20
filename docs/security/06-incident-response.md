# 06 — Incident Response

## 1. Severity matrix

| Sev | Definition | Examples | Response |
|---|---|---|---|
| SEV-1 | Confirmed breach of tenant data, audit-chain integrity failure, or compromised filing-path integrity | Cross-tenant read confirmed; chain verification fails; tampered computation approved | Immediate: platform kill switches as needed, IR bridge, preserve evidence, 72h GDPR clock starts on personal-data confirmation, tenant notification |
| SEV-2 | Contained security failure, no confirmed data exposure | Injection reached a blocked tool call at volume; credential leak caught pre-abuse; RLS bug found by canary before exploitation | Same-day: contain, rotate, root-cause; disclosure evaluation |
| SEV-3 | Control degradation | Scanner gate bypassed; audit lag; cert expiry near-miss | Ticketed, 7-day fix SLA, trend review |
| SEV-4 | Hardening finding | Pentest medium; noisy alert | Backlog with SLA |

## 2. Playbooks (extend the Phase 8 runbook set; each: detect → contain → eradicate → recover → learn)

| Playbook | Notes specific to TaxOS |
|---|---|
| `ir-cross-tenant` | Canary/report trigger → freeze affected tenants' sessions (revocation list), snapshot DB + logs *before* fixes, RLS/cache/WS forensics, controller notification path (processor role, doc 03 §3) |
| `ir-audit-chain` | **Treat as SEV-1 until proven benign** (serializer bug vs tampering): verify against WORM anchors to bound the tamper window; if genuine: insider procedure, legal hold on evidence containers |
| `ir-agent-compromise` | Kill switch `ff_agent_runs_enabled` off → park all runs; preserve run traces (they are the forensic record — FR-302 pays off here); replay injection through fixtures; add attack class to suite before re-enable |
| `ir-corpus-poisoning` | End-date poisoned docs (provenance preserved); identify affected answers via `knowledge_answer` lineage (which citations touched the doc); flag downstream work items for re-review — **the citation graph makes blast-radius computable**, which is the whole point |
| `ir-credential-leak` | Rotation procedure per credential class (KV versions, OIDC subjects, DB roles); scoped by design (per-service identities bound the blast radius) |
| `ir-supply-chain` | Dependency/image compromise: pin-freeze, rebuild from last-good SHA (signed images make "last good" provable), diff release BOMs |
| `ir-model-misbehaviour` | Not security but same muscle: invariant-violation spike → model/prompt rollback via registry stage flip + prompt version revert |

## 3. Evidence preservation rules (before any remediation)

Snapshot: DB (PITR point marked), Log Analytics export for the window, relevant Blob (WORM already immutable — its job), run traces, release BOM of the running version. The anchored audit chain gives post-incident *proof of what happened when* — the IR plan's unique asset; preserving the chain tip is step zero of every playbook.

## 4. Communications

Internal: bridge channel + status page in `/admin/system` (P5-visible). Tenant/controller: notification templates (facts, scope, actions, contacts) — processor obligations per DPA; no speculation, update cadence committed. Regulatory: controller leads GDPR notifications; TaxOS supplies the technical annex from evidence above. Post-incident: blameless review within 5 days → actions tracked as issues → runbook/fixture updates (every incident must leave the suite stronger — the corpus/injection suites are living catalogues by policy).

## 5. Readiness

Semi-annual tabletop (rotating scenario, doc 04 §4) · kill switches tested in staging chaos drills (Phase 2 doc 08 §6) · IR contact card in repo README (security@, response SLA) · the `just` ops toolkit works in incidents because it's the same toolkit used daily (Phase 6 doc 07 §4 — no special incident tooling to fumble at 2am).
