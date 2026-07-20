# Phase 9 — Security Programme

**Product:** Enterprise Agentic Tax Operating System (TaxOS)
**Status:** Complete — awaiting stakeholder review
**Inputs:** Phase 2 doc 07 (security architecture), Phase 4 (corpus trust boundary), Phase 8 (network/identity), NFR-01/02/03/04
**Last updated:** 2026-07-20

## Posture summary (what is already structural)

Security in TaxOS is predominantly **architecture, verified by tests** — not a bolted-on layer. The structures phases 2–8 built: layered authZ (RBAC→ABAC→RLS), hash-chained audit with WORM anchoring, agent capability confinement (Tool Gateway + IAM + network policy — three independent layers), pseudonymisation before LLM egress, private-endpoint-only data plane, zero stored credentials, signed rule packs, governed corpus ingestion. This phase's job: **enumerate the threats systematically, catalogue the AI-specific attacks, specify the verification suite, and map controls to the frameworks buyers audit against.**

## Document map

| # | Document | Covers |
|---|----------|--------|
| 01 | [Threat Model](01-threat-model.md) | Trust boundaries, full STRIDE analysis, top attack trees, risk register |
| 02 | [AI & Agent Security](02-ai-security.md) | Prompt-injection catalogue (OWASP LLM Top 10 mapped), RAG security, agent-isolation verification |
| 03 | [Data Privacy & GDPR](03-data-privacy.md) | PII detection pipeline, lawful basis, DPIA summary, data-subject rights, retention |
| 04 | [Security Testing](04-security-testing.md) | SAST/DAST/dependency posture, the security unit-test suite, injection suite, pentest scope |
| 05 | [Compliance Mappings](05-compliance-mappings.md) | ISO 27001 Annex A, SOC 2 TSC, OWASP ASVS L2, OWASP LLM Top 10 — control matrices |
| 06 | [Incident Response](06-incident-response.md) | Severity matrix, playbooks, evidence preservation, tenant comms |

## Security principles (operative restatement)

1. **Deny by default, everywhere** — RBAC guards, RLS, NSGs, tool grants, egress: absence of a rule means no.
2. **Independent layers** — every critical property (tenant isolation, agent confinement, audit integrity) is enforced by ≥2 mechanisms that fail independently.
3. **Evidence over assertion** — controls exist when a test or artifact proves them (the invariant suite, chain verification, rehearsal logs).
4. **The AI surface is hostile-input territory** — all retrieved/ingested/user text reaching prompts is untrusted; agent outputs are structured or rejected.
5. **Compromise is planned for** — IR playbooks, blast-radius design, anchored audit for post-incident truth.
