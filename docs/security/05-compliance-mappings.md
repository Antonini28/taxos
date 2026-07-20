# 05 — Compliance Control Mappings

**Honest framing:** TaxOS is *mapped*, not certified. These matrices are the artifact that makes certification an audit exercise rather than an engineering project — and the artifact a Big Four security review asks for on day one. Format: control → implementing mechanism → evidence artifact.

## 1. ISO 27001:2022 Annex A (condensed to the load-bearing controls)

| Annex A | Control | Mechanism | Evidence |
|---|---|---|---|
| 5.15/5.18 | Access control & rights | RBAC+ABAC+RLS; PIM JIT; quarterly access review | Role matrix artifact; review logs (ops calendar) |
| 5.23 | Cloud services security | Azure Policy guardrails; private endpoints; residency deny-rules | TF policies; tfsec reports |
| 5.28 | Evidence collection | Evidence packs; anchored audit chain | Chain-verify job output; pack samples |
| 6.3 | Awareness | Runbooks + onboarding docs | docs/runbooks |
| 8.2/8.3 | Privileged access / info restriction | PIM; re-identification API w/ purpose; break-glass audited | Activity logs |
| 8.8 | Technical vulnerability mgmt | §04 pipeline + SLAs | Monthly posture report |
| 8.9 | Configuration mgmt | IaC-only changes; drift detection | Nightly drift reports |
| 8.12 | Data leakage prevention | Pseudonymisation; egress design; R-03 register entry (partial) | DPIA annex |
| 8.13 | Backups | PITR + geo; verified restores | Rehearsal logs |
| 8.15/8.16 | Logging & monitoring | OTel estate; append-only audit; alerts→runbooks | Dashboards-as-code; alert configs |
| 8.24 | Cryptography | TLS/AES/field-level/signing; KV custody; rotation calendar | Key inventory; rotation logs |
| 8.25–8.31 | Secure SDLC | The entire Phase 6 gate set + review rules + env separation | CI configs; branch protection |
| 8.32 | Change management | PR-only + protected branches + release BOM + migration gating | Release annotations |

## 2. SOC 2 Trust Services Criteria

| TSC | Mechanism highlights |
|---|---|
| CC1 (org/integrity) | Documented ownership (docs), SoD in both product *and* SDLC (protected branches, dual review on sensitive paths) |
| CC2/CC3 (communication, risk) | This doc set; risk register w/ quarterly review (01 §4) |
| CC4 (monitoring) | Invariant+security suites in CI (continuous control monitoring — the tests *are* the monitoring); drift detection; posture report |
| CC5/CC6 (control activities, access) | Layered authZ; MI-only cloud access; secretless CI; KV custody; offboarding via Entra group removal (single source) |
| CC7 (ops) | SLOs, alerts→runbooks, IR plan (doc 06), capacity via KEDA + budgets |
| CC8 (change) | IaC + pipelines + release BOM + rollback drills |
| CC9 (risk mitigation) | DR rehearsals; vendor mgmt (sub-processor list; Azure attestations inherited) |
| A1 (availability) | HA design (Phase 2 doc 08 §4); measured SLOs |
| C1 (confidentiality) | Tenancy stack; classification (03 §1); NDA-relevant data flows documented |
| PI1 (processing integrity) | **The platform's whole thesis:** deterministic engines, reproducibility, approval gates, chain — TaxOS is unusually strong here and the demo shows it |
| P (privacy) | Doc 03 GDPR machinery |

## 3. OWASP ASVS 4.x — Level 2 posture statement

Chapters V1–V14 assessed; design meets L2 across the board with these callouts: V2 AuthN delegated to IdP (dev-issuer isolated to non-prod by config assertion) · V4 access control = triple layer, matrix-tested · V5 validation = Pydantic-everywhere + output encoding + CSV escapes · V7 error/logging = problem+json (no leakage) + PII-free logs · V8 data protection = doc 03 · V9 communications = TLS everywhere · V10 malicious code = signed images, locked deps · V11 business logic = the invariant suite (SoD, state machines, hash binding) · V12 files = upload controls · V13 API = the whole Phase 2 doc 06 discipline · V14 config = IaC + policy guardrails. Gap register: V2.8 (WebAuthn step-up for approvals — enterprise backlog), V8.3.4 (full DLP — R-03).

## 4. OWASP LLM Top 10 → mapped in doc 02 §2 (kept beside the attack catalogue it belongs to)

## 5. UK-specific obligations worth naming (differentiator in this domain)

| Regime | Relevance | TaxOS posture |
|---|---|---|
| SAO (Senior Accounting Officer) | P1 personally certifies "appropriate tax accounting arrangements" | Evidence-by-default + readiness checklists = the certification support pack |
| CCO (Corporate Criminal Offence, CFA 2017) | "Reasonable prevention procedures" defence | Documented controls, fraud detection, audit trail — the procedures, evidenced |
| UK GDPR + DPA 2018 | Doc 03 | — |
| MTD (Making Tax Digital) | Digital links rules — no manual re-keying in the return chain | Lineage-complete pipeline *is* digital-links compliance; documented mapping when e-filing lands (W-01) |
