# 04 — Security Testing

## 1. Pipeline-integrated scanning (always on)

| Layer | Tool | Gate |
|---|---|---|
| Secrets | gitleaks (pre-commit + CI) | Any hit blocks |
| SAST | ruff security rules (bandit set) + CodeQL (GitHub Advanced Security) | Critical/high block |
| Dependencies | `uv lock --check` + trivy (Python/npm) + licence allow-list | Critical block; high = 7-day SLA ticket |
| Containers | trivy image scan + cosign sign/verify (deploy verifies signature) | Critical block |
| IaC | tfsec/checkov on `infra/` | High block |
| DAST | OWASP ZAP baseline vs staging (nightly) — authenticated scan with per-role contexts | New alert = ticket; medium+ = block promotion |
| Frontend | npm audit + CSP report-only monitoring → enforce | — |

## 2. The security test suite (extends the Phase 6 invariant suite — these run in CI, forever)

**Tenancy (TB7):**
`every_business_table_has_rls_policy` (schema introspection — new tables can't forget) · cross-tenant read/write attempts via API, repos, cache keys, WS subscriptions, Blob paths (all must fail + audit) · canary-row detector wired in staging.

**AuthZ (TB1):**
route-walk: every route has a guard (allow-list: health, docs-nonprod) · role matrix test: for each (role × mutating endpoint) assert expected 200/403 from a generated matrix file — **the authorisation model is a versioned artifact whose changes are visible in PR diffs** · SoD suite (prepare/approve permutations incl. role-change-mid-flow) · IDOR fuzzing: object ids across tenants/entities (schemathesis + custom).

**Audit & evidence (TB8):**
unaudited-mutation, chain-tamper-detection, immutability-guard tests (Phase 6) · WORM policy assertion (infra test attempts delete within retention → denied) · anchored-head verification job test.

**Session/JWT:**
expired/wrong-aud/wrong-issuer/alg-none/stripped-signature tokens → 401 · revoked refresh reuse → session-family invalidation (rotation-theft detection) · cookie flags asserted (httpOnly/SameSite/secure).

**Injection (classical):**
SQLi via schemathesis + targeted repo fuzz (parameterisation makes this a regression tripwire, not a hunt) · CSV/formula injection on every export path · path traversal on uploads/doc-viewer · SSRF: the two egress-capable components (corpus adapters, webhook sender R4) tested against internal-IP/metadata-endpoint targets with allow-list enforcement.

## 3. AI security suite (the injection catalogue, executable — doc 02 §1/§4)

- **Fixture corpus:** `evals/security/injections/` — per-class (PI-1..10) attack documents/memos/chat inputs, versioned like golden sets; new attack publications get fixtures within a sprint (the suite is a living catalogue).
- **Assertions per run:** no undeclared tool call attempted (and if attempted: 403 + telemetry) · no scope-external identifier in any output (invariant layer) · no citation that fails resolution · budgets respected · run outcome ∈ {completed-clean, escalated} — never silent-compliance with injected instructions.
- **Scoring:** injection suite reports *containment rate per layer* (screened at ingest / refused by model / blocked by gateway / caught by invariant) — measuring **which layer caught it**, because "the model refused" alone is not a control (defence-in-depth verified as depth, not luck).
- Isolation checklist tests (doc 02 §4, items 1–8) run in CI (unit/integration) + infra assertions in the TF pipeline.

## 4. Manual & periodic

| Activity | Cadence | Scope |
|---|---|---|
| Internal pentest sprint (self-conducted, methodology-documented: ASVS L2 checklist + PortSwigger-style auth/IDOR passes) | Per release train | Full staging estate |
| External pentest (enterprise posture; budgeted) | Annual | Web + API + cloud config review |
| AI red-team session (novel injection attempts beyond fixture classes; findings → new fixtures) | Per release train | Agent workspace, doc intake, corpus |
| Access review | Quarterly (ops calendar, Phase 8) | Entra groups, PIM, DB roles, KV, tool grants |
| Tabletop IR exercise | Semi-annual | One scenario from doc 06 playbooks |

## 5. Vulnerability management

Single intake (scanner findings, pentest, disclosure email `security@`) → triage SLA: critical 24h / high 7d / medium 30d → tracked as issues with the `security` label → fix PRs reference finding ids → monthly posture report (open by severity, MTTR trend) rendered to `/admin/system` for P5 — the platform's own dashboard eats this dogfood.
