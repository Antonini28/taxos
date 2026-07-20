# 07 — Security Architecture

*Architecture-level design. The full security programme (threat model, test suite, control mappings, prompt-injection catalogue) is Phase 9; this document fixes the load-bearing structures Phase 9 will verify.*

## 1. Identity & authentication (ADR-007)

| Concern | Design |
|---|---|
| Human identity | OIDC against **Microsoft Entra ID** (the Big Four reality); authorization-code + PKCE flow; MFA enforced at the IdP (conditional access), not reimplemented in-app |
| Local/dev + demo | Built-in OIDC-compatible dev issuer so the platform runs without a corporate tenant (demo environments); same code path, different issuer config |
| Sessions | Short-lived access JWT (15 min) + rotating refresh token (httpOnly, secure, SameSite=strict cookie); revocation via Redis denylist checked on refresh |
| Service identity | Client-credentials flow per service (taxos-agents, workers) with distinct app registrations; **Azure Managed Identity** for Azure-resource access (Key Vault, Blob, Service Bus) — zero credentials in config |
| Token claims | `sub`, `tenant_id`, `roles[]`, `entity_scopes[]`, `session_id`; tokens are *authorisation input*, never the decision (fresh policy check server-side per request) |

## 2. Authorisation: layered RBAC + ABAC

Decision order (all layers must pass — deny wins):

```
1. Route guard (RBAC):   does any role permit this action?        e.g. approval:grant → REVIEWER|HEAD_OF_TAX
2. Policy check (ABAC):  attributes — entity scope, tenant match,
                         SoD (actor ≠ preparer), workflow state,
                         4-eyes thresholds (enterprise)
3. Data layer (RLS):     Postgres row-level security on tenant_id —
                         even buggy application code cannot cross tenants
```

Roles (MVP): `ADMIN`, `PREPARER`, `REVIEWER`, `APPROVER`, `READ_ONLY`, `AUDITOR` (read + audit-log access, no business writes). Policies are code (a small internal policy engine: pure functions over a typed `AuthzContext`), unit-tested like tax rules; OPA was considered and rejected at this scale — an external policy daemon adds an ops dependency without adding expressiveness we need (revisit trigger: multi-service policy sharing).

**Segregation of duties is data-driven:** the workflow module records preparer/reviewer per work item; the SoD policy reads those facts. SoD tests are part of the acceptance suite (US-402/501).

## 3. Agent security (the novel surface)

Threats: prompt injection (via ingested documents/knowledge), tool misuse, data exfiltration through LLM egress, runaway cost.

| Control | Mechanism |
|---|---|
| Capability confinement | Tool Gateway surface (doc 06 §2): no approval/filing/user-management endpoints exist for agents; per-agent tool grants verified server-side per call (ADR-012) |
| Blast-radius isolation | taxos-agents is a separate service with its own identity; its DB account has zero direct business-table grants |
| Injection containment | All retrieved/ingested text entering prompts is delimited + tagged untrusted; agent outputs that would trigger tool calls are schema-validated (structured outputs only — free-text can't call tools); instruction/data separation tested in Phase 9 suite |
| Egress minimisation | Pseudonymisation at ingest (doc 04 §6) means LLM-bound context carries pseudonyms; per-run context assembled by allow-listed retrievers, not raw table access |
| Cost & loop control | Per-run budgets (tokens, tool calls, wall clock — doc 06 §5); Supervisor plans are bounded DAGs, recursion capped; circuit breaker on provider |
| Human gate | GP-1: agents end at `AWAITING_HUMAN_REVIEW` — architecturally, because the transition to `APPROVED` requires an approval record with a human actor and SoD pass |

## 4. Secrets & key management

- **Azure Key Vault** for all secrets (DB creds, API keys, pseudonymisation keys, pack-signing keys); accessed via Managed Identity at boot; local dev uses `.env` + docker secrets with a committed `.env.example` and a secret-scanning pre-commit hook (gitleaks) + CI gate.
- Rotation: DB credentials and service secrets rotated via IaC-driven schedule; pseudonymisation keys are **versioned, never deleted** (old data must stay resolvable to authorised eyes) — key version stored alongside each pseudonym.
- Rule-pack signing: packs signed at publish (Ed25519, key in Key Vault); PackLoader verifies signature + hash before any computation (supply-chain control on tax logic itself).

## 5. Data protection summary

| State | Control |
|---|---|
| In transit | TLS 1.2+ everywhere, including intra-Azure service-to-service; HSTS at edge |
| At rest | Azure storage/DB encryption (platform-managed keys MVP; CMK via Key Vault as enterprise option) |
| In use (app) | PII classification at ingest → pseudonymisation; field-level encryption for the pseudonym mapping table |
| In evidence | WORM containers with retention policies (doc 04 §5) |
| In LLM context | Pseudonyms only; provider chosen with no-training/enterprise data terms (Azure OpenAI) |

## 6. Audit chain (ADR-009) — why it's a security control

The append-only hash-chained `audit_event` table (doc 04 §3) is the platform's non-repudiation mechanism: every mutation commits atomically with its audit record; chain verification (`H(prev ‖ payload) == event_hash` for the full sequence) runs as a scheduled integrity job and on evidence-pack export, and chain heads are periodically anchored to WORM Blob storage (an insider with DB access cannot silently rewrite history without breaking the anchored chain). This converts "we log things" into "we can prove the log."

## 7. Threat-model preview (STRIDE headlines — full model in Phase 9)

| STRIDE | Top threat | Primary mitigations (already in architecture) |
|---|---|---|
| Spoofing | Stolen tokens / forged service identity | Short-lived JWTs, PKCE, managed identities, per-service registrations |
| Tampering | Rule-pack or computation manipulation | Pack signing, computation snapshots + inputs_hash, audit chain |
| Repudiation | "I never approved that" | Content-hash-bound approvals, hash-chained audit, anchored heads |
| Information disclosure | Cross-tenant leak; PII to LLM | RLS + tenant-keyed caches + WS server-side filtering; pseudonymisation |
| Denial of service | Upload floods, agent loops | Per-tenant limits, queue isolation, run budgets, circuit breakers |
| Elevation of privilege | Agent reaching forbidden actions; preparer self-approval | Tool Gateway construction, layered authZ, SoD policy + tests |
