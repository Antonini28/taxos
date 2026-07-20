# 07 — MVP Definition & Enterprise Edition

## 1. MVP definition (Release R1)

### One-sentence definition

> **The MVP is a deployed, governed, agentic UK VAT compliance cycle:** upload real-shaped ERP data → validation → deterministic 9-box computation with full lineage → anomaly detection → agent-orchestrated workflow ending at a human approval gate → executive dashboard and exportable evidence pack — running on Azure behind enterprise auth with an immutable audit log.

### Why this MVP cut (and not something broader/thinner)

| Alternative considered | Rejected because |
|---|---|
| "AI tax chatbot with RAG" first | Commodity demo; proves nothing about data engineering, governance, or tax depth; every candidate has one |
| Multi-tax shallow coverage (VAT+CT+WHT toy versions) | Breadth of toys reads as a student project — the brief's explicit anti-goal; depth in one cycle demonstrates production thinking |
| Fraud-detection-only analytics product | Strong ML story but loses the *agentic operating system* differentiator and the workflow/governance evidence |
| Full platform, no deployment | An undeployed enterprise platform is a contradiction; hiring reviewers check the running system first |

The chosen MVP forces every architectural muscle the target roles assess: data pipelines, deterministic domain engines, multi-agent orchestration, human-in-the-loop governance, ML, dashboards, auth, audit, cloud, CI/CD — in one coherent, demoable story.

### MVP scope fence

**In (R1):** FR-101–104, FR-201, FR-204, FR-205, FR-301–304, FR-306, FR-501 (rules + Isolation Forest), FR-506, FR-601, FR-602 (VAT), FR-604, FR-701, FR-702, FR-704-minimal; NFR-01/02/04/10/11/12.

**Out (deferred, with the release that catches them):** RAG knowledge base (R2), CT engine (R2), SHAP scoring (R2), chat workspace beyond run-instruction (R2), multi-tenant activation (R3), regulatory monitoring (R3), forecasting (R2), public API (R4), WHT/TP (R4).

**Never (W-register):** autonomous filing, uncited tax advice, personal tax — see doc 04 §3.

### MVP success criteria

1. The six-step demo script in doc 05 (R1 exit criteria) runs end-to-end on the deployed Azure environment.
2. A reviewer can break nothing by acting maliciously within the UI (SoD enforced, RBAC enforced, quarantine respected).
3. Every number on screen traces to source in ≤ 3 clicks.
4. Fresh-clone developer onboarding to running local stack ≤ 15 minutes (docker compose).
5. CI runs tests, linting, type checks, secret scanning; CD deploys on merge to main.

## 2. Enterprise edition definition (R3–R4 cumulative)

The enterprise edition is what a Big Four managed-services practice could pilot with real clients. It adds, on top of MVP+R2:

| Pillar | Capability | Requirements |
|---|---|---|
| **Multi-client operation** | Hard tenant isolation (RLS + isolation test suite), tenant-scoped ABAC, cross-tenant anonymised benchmarking, white-label reporting | FR-703, P6 persona |
| **Regulatory intelligence** | Source monitoring → relevance classification → impact assessments in review queue | FR-404 |
| **Reporting automation** | Agent-assembled, human-approved board packs on schedule (PDF/PPTX) | FR-603 |
| **Full security posture** | Prompt-injection defence suite, PII detection, DPIA, ISO 27001/SOC 2 control mapping, pen-test-style security tests | NFR-02/03/15 |
| **Operational maturity** | SLOs + error budgets, DR rehearsal (RPO 1h/RTO 4h), model drift monitoring with alerting, cost governance | NFR-05/08/14, FR-505 |
| **Extensibility** | Jurisdiction content packs, public OpenAPI + webhooks, reference ERP connector | FR-206, FR-706, FR-106 |
| **Extended tax coverage** | WHT with treaty rates, TP variance monitoring, knowledge graph reasoning | FR-203, FR-207, FR-405 |

### Edition comparison (productised framing)

| | **MVP / Team** | **Professional (R2)** | **Enterprise (R3–R4)** |
|---|---|---|---|
| Tax coverage | UK VAT | + UK CT, forecasting | + WHT, TP monitoring |
| Agents | Supervisor, Data, VAT, Fraud, Reporting, Approval | + Research, Critic, Document, CT | + Regulatory Monitor, full team |
| Knowledge | — | Cited RAG on HMRC corpus | + Knowledge graph, reg-change intelligence |
| ML | Rules + Isolation Forest | + GBM scoring, SHAP, registry | + Drift monitoring, feedback-loop retraining |
| Tenancy | Single tenant | Single tenant | Multi-tenant with isolation guarantees |
| Governance | RBAC, SoD, audit log, approvals | + Eval harness in CI | + ABAC, PII detection, control mappings, DR |
| Interfaces | Web app | + Chat workspace | + Public API, webhooks, white-label reports |

## 3. Discovery sign-off checklist

- [x] Business problem quantified with cost-of-inaction model
- [x] Market sized (TAM/SAM/SOM) and honest positioning vs incumbents & Big Four platforms
- [x] Gap analysis identifies a defensible wedge (governed agentic execution + explainable risk + evidence-by-default)
- [x] Six personas with success measures, mapped to capabilities
- [x] 40+ functional requirements and 15 NFRs, MoSCoW-prioritised, with explicit non-goals
- [x] Four-train roadmap with exit criteria and sequencing rationale
- [x] Seed backlog: 30 ranked stories with Gherkin acceptance criteria and DoD
- [x] MVP defined by scope fence + success criteria; enterprise edition defined by pillar
- [ ] **Stakeholder review** ← you are here

**Next phase gate:** on approval of this discovery package, Phase 2 (Enterprise System Architecture) begins, consuming FR/NFR IDs as design inputs and recording decisions as ADRs.
