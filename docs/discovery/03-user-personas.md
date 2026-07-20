# 03 — User Personas

Six personas drive all requirements and user stories. Codes `P1`–`P6` are referenced throughout the backlog. Personas are grounded in real enterprise tax-function structures (in-house MNE tax department + Big Four managed-services delivery model).

---

## P1 — Head of Tax ("Amara")

| Attribute | Detail |
|---|---|
| Role | Group Head of Tax, UK-headquartered MNE (~£2bn revenue, 40 countries) |
| Reports to | CFO; personally exposed via SAO certification |
| Tech comfort | Consumes dashboards; will not touch raw data |
| **Goals** | Zero late filings; no penalty events; defensible positions; credible ETR story for the board; do more with a flat headcount |
| **Pains** | Finds out about problems at deadline; can't quantify group-wide exposure; audit enquiries derail the team for weeks; can't evidence "reasonable procedures" (CCO) without a paper chase |
| **Needs from TaxOS** | Live compliance calendar with RAG status; quantified risk register; one-click evidence packs; approval queue for anything agents want to execute |
| **Success measure** | "I can answer any board or HMRC question about our tax position in one day, not three weeks." |
| Key screens | Executive Dashboard, Risk Intelligence Centre, Approvals |

---

## P2 — Tax Operations Manager ("Daniel")

| Attribute | Detail |
|---|---|
| Role | Manages the compliance cycle: VAT returns, CT600 preparation, WHT, payroll taxes across UK entities |
| Tech comfort | Power user — Excel expert, some SQL, lives in the ERP |
| **Goals** | Hit every deadline with fewer manual steps; stop re-keying data; catch errors before review, not after filing |
| **Pains** | Month-end data extraction takes days; every entity has spreadsheet quirks; reviewing junior work is slower than doing it; no version control on computations |
| **Needs from TaxOS** | Automated ingestion + validation of ERP extracts; agent-prepared draft returns with exceptions flagged; side-by-side source-to-figure traceability; workflow states (prepared → reviewed → approved → filed) |
| **Success measure** | "A VAT return that took 3 days of prep now takes 2 hours of review." |
| Key screens | Workflow Management, VAT/CT/WHT Analysis, Document Management, Agent Chat Workspace |

---

## P3 — Tax Risk & Audit Lead ("Priya")

| Attribute | Detail |
|---|---|
| Role | Owns tax risk register, audit responses, SAO/CCO evidence, internal controls over tax |
| Tech comfort | Analytical; comfortable with BI tools; sceptical of black-box AI |
| **Goals** | Continuous controls monitoring; every figure traceable; fraud/anomalies surfaced early; enquiry responses in days |
| **Pains** | Risk assessment is annual and subjective; anomaly detection is sampling-based; evidence reconstruction is archaeology |
| **Needs from TaxOS** | Explainable risk scores (SHAP-level "why"); anomaly queue with disposition workflow; immutable audit log of every agent/human action; evidence pack generator per entity/period/tax |
| **Success measure** | "When HMRC asks 'why is this number what it is', the answer is a click, with lineage." |
| Key screens | Fraud Detection Centre, Risk Intelligence Centre, Audit Readiness, Activity Logs |

---

## P4 — CFO / Finance Director ("Marcus")

| Attribute | Detail |
|---|---|
| Role | Group CFO; consumer of tax outputs, owner of the P&L impact |
| Tech comfort | Dashboard-level only; 5 minutes of attention |
| **Goals** | Predictable cash tax; no surprises; ETR narrative for investors; tax function cost under control |
| **Pains** | Tax is a black box that reports quarterly and asks for budget annually |
| **Needs from TaxOS** | Executive dashboard: cash tax forecast, ETR bridge, exposure quantification, compliance status heat map, cost-of-function KPIs; scheduled board-pack export |
| **Success measure** | "Tax status in my Monday pack, automatically, and it's current." |
| Key screens | Executive Dashboard, Reports Centre |

---

## P5 — Tax Technology Lead / Platform Admin ("Sofia")

| Attribute | Detail |
|---|---|
| Role | Owns tax systems; integrates ERP feeds; manages users, entities, and configuration (the user's own former role at PwC — the persona the portfolio speaks to directly) |
| Tech comfort | Engineer: Python, SQL, APIs, Power BI |
| **Goals** | Reliable pipelines; observable system; controlled rollout of AI features; clean RBAC; no shadow IT |
| **Pains** | Fragile point-to-point integrations; no monitoring; every new tool is a new silo; auditors question system controls |
| **Needs from TaxOS** | Connector framework with retry/monitoring; admin panel (users, roles, entities, jurisdictions, feature flags); API keys & docs; model monitoring (drift, cost, latency); system health dashboards |
| **Success measure** | "I can onboard a new entity's data feed in a day and prove the pipeline's integrity to audit." |
| Key screens | Administration, API Management, System Health, AI Model Monitoring |

---

## P6 — Big Four Engagement Manager ("James") *(channel persona — enterprise edition)*

| Attribute | Detail |
|---|---|
| Role | Manages tax compliance managed-service delivery for 15 client groups at a Big Four firm |
| Tech comfort | Platform power user |
| **Goals** | Standardised delivery across clients; margin improvement via automation; client-facing transparency portal |
| **Pains** | Every client is a bespoke spreadsheet estate; utilisation eaten by data prep; no cross-client benchmarking |
| **Needs from TaxOS** | Multi-tenant workspace per client with hard data isolation; cross-tenant (anonymised) benchmarking; white-label reporting; engagement-level workflow oversight |
| **Success measure** | "Same platform, fifteen clients, one team — with provable data segregation." |
| Key screens | Tenant switcher, Workflow Management, Reports Centre, Admin |

---

## Persona → capability matrix (summary)

| Capability domain | P1 | P2 | P3 | P4 | P5 | P6 |
|---|---|---|---|---|---|---|
| Executive & board reporting | ● | ○ | ◐ | ● | ○ | ● |
| Compliance workflow automation | ◐ | ● | ◐ | ○ | ○ | ● |
| Risk, fraud & anomaly analytics | ● | ◐ | ● | ◐ | ○ | ◐ |
| Audit readiness & evidence | ● | ◐ | ● | ○ | ◐ | ● |
| Knowledge & research (RAG) | ◐ | ● | ● | ○ | ○ | ● |
| Platform administration & observability | ○ | ○ | ○ | ○ | ● | ◐ |
| Approvals & governance | ● | ● | ● | ○ | ◐ | ● |

● primary user ◐ secondary ○ rare
