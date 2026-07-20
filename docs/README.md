# TaxOS Documentation Portal

One index, organised by **reader**, not by phase. (The phase structure below it remains the authoritative technical corpus — these guides curate it.)

## By audience

| You are… | Read |
|---|---|
| **Evaluating the project** (recruiter, interviewer, reviewer) | [Repo README](../README.md) → [Business case](business/business-case.md) → [Executive presentation](business/executive-presentation.md) |
| **A developer joining the codebase** | [Developer guide](guides/developer-guide.md) → [Backend standards](backend/README.md) → [Frontend package](frontend/README.md) |
| **Deploying or operating it** | [Deployment guide](guides/deployment-guide.md) → [Maintenance guide](guides/maintenance-guide.md) → [Runbooks](runbooks/) |
| **Using the platform** (tax professional) | [User manual](guides/user-manual.md) |
| **Auditing it** (security/compliance) | [Security programme](security/README.md) → [Compliance mappings](security/05-compliance-mappings.md) → [Audit chain design](architecture/adr/ADR-009-audit-log-hash-chain.md) |
| **Integrating with it** | API reference: generated OpenAPI (`/api/v1/openapi.json`; Swagger UI in non-prod) — conventions in [API design](architecture/06-api-design.md) + [implementation standards](backend/05-api-standards.md) |

## The technical corpus (Technical Design Document)

The TDD is not a separate document that would drift — it **is** this corpus, phase by phase, with ADRs as the decision record:

| Phase | Set | Contents |
|---|---|---|
| 1 | [discovery/](discovery/README.md) | Problem, market, personas, requirements, roadmap, backlog |
| 2 | [architecture/](architecture/README.md) | C4 models, data/eventing/API/security/deployment/observability + **ADR-001..018** |
| 3 | [ai/](ai/README.md) | Framework evaluation, agent system design, 13 agent specifications, eval framework |
| 4 | [knowledge/](knowledge/README.md) | Corpus governance, chunking/embedding, hybrid retrieval, knowledge graph, citations & grounding |
| 5 | [ml/](ml/README.md) | Problem map, anomaly detection, supervised models, forecasting, explainability, MLOps |
| 6 | [backend/](backend/README.md) | Repository standards, audited UoW, async patterns, API kit, testing patterns, local dev |
| 7 | [frontend/](frontend/README.md) | Design system, IA, flagship screen specs, page catalogue, frontend architecture |
| 8 | [cloud/](cloud/README.md) | Terraform estate, network/identity, promotion, Kubernetes target, operations |
| 9 | [security/](security/README.md) | Threat model, AI security, privacy/GDPR, security testing, compliance, IR |
| 10 | [testing/](testing/README.md) | Consolidated programme, performance testing, E2E, quality gates |
| 11 | guides/ + business/ | This layer |

## Documentation standards

Docs-as-code (ADR-004): Markdown + Mermaid, PR-reviewed, versioned with the system they describe. Every doc carries status + date. Guides **curate and link** — they never duplicate normative content (duplication is where docs go to lie). User-facing changes must update the relevant guide in the same PR (release-readiness checklist item).
