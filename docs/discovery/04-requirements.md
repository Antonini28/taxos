# 04 — Requirements Specification

Prioritisation: **MoSCoW** (M = Must for MVP, S = Should for v1.x, C = Could for enterprise edition, W = Won't in current horizon).
Every requirement carries an ID used by user stories (doc 06) and, later, ADRs and test plans.

## 1. Functional requirements

### FR-100 — Data platform & ingestion

| ID | Requirement | Priority | Personas |
|----|-------------|----------|----------|
| FR-101 | Ingest transactional data (GL journals, AP/AR sub-ledger, invoices, payroll extracts) via file upload (CSV/XLSX), and via connector API for ERP extracts | M | P2, P5 |
| FR-102 | Validate every ingested batch against schema + business rules (entity exists, period open, balances reconcile, VAT codes valid); produce a validation report; quarantine failures | M | P2, P5 |
| FR-103 | Maintain full data lineage: every derived figure traceable to source rows and transformation version | M | P3, P5 |
| FR-104 | Master data management: legal entities, jurisdictions, VAT registrations, tax codes, calendars/deadlines | M | P5 |
| FR-105 | Document ingestion: PDF/DOCX/XLSX/email upload with OCR + structured extraction (invoices, certificates, assessments) | M (invoices) / S (rest) | P2 |
| FR-106 | Scheduled/streaming ERP connectors (SAP, Oracle, Dynamics) with retry, checkpointing, and monitoring | C | P5 |

### FR-200 — Tax computation & compliance (deterministic core)

| ID | Requirement | Priority | Personas |
|----|-------------|----------|----------|
| FR-201 | UK VAT return preparation (9-box) from transactional data, incl. partial exemption handling and reverse charge, as a **versioned deterministic rule engine** | M | P2 |
| FR-202 | UK Corporation Tax computation skeleton: accounting profit → taxable profit with adjustment schedule (depreciation/capital allowances, disallowables, losses, group relief placeholders) | M | P2 |
| FR-203 | Withholding tax calculator: payment classification, treaty-rate lookup, WHT liability schedule | S | P2 |
| FR-204 | Compliance calendar: obligations per entity/jurisdiction with statutory deadlines, RAG status, ownership | M | P1, P2 |
| FR-205 | Every computation reproducible: same inputs + same rule version ⇒ identical output (bit-for-bit), with stored computation snapshot | M | P3 |
| FR-206 | Jurisdiction content packaged as versioned data ("content packs") — adding a jurisdiction must not require core code changes | S (architecture M) | P5 |
| FR-207 | Transfer pricing monitoring: intercompany transaction register, policy-rate vs actual-rate variance flags | C | P1, P3 |

### FR-300 — Agentic AI workforce

| ID | Requirement | Priority | Personas |
|----|-------------|----------|----------|
| FR-301 | Multi-agent orchestration: Supervisor plans and routes work to specialist agents (Data, VAT, CT, Fraud, Research, Reporting, etc.) with shared state and memory | M | all |
| FR-302 | Every agent action recorded: inputs, tools called, outputs, tokens/cost, latency, confidence — queryable per work item | M | P3, P5 |
| FR-303 | **Human-approval gates:** agents may prepare and recommend; any state change of record (submit return, post adjustment, send report externally) requires explicit human approval with recorded approver identity | M | P1, P3 |
| FR-304 | Agent chat workspace: users converse with the agent team about live data ("why did Box 4 increase 40% vs last quarter?") with citations to data lineage and knowledge sources | M | P2, P3 |
| FR-305 | Reflection/critic pass: specialist agent outputs are reviewed by a critic agent against rubric before reaching human review; failures loop back with feedback (bounded retries) | S | P3 |
| FR-306 | Escalation policy: on low confidence, rule conflict, or missing data, agents escalate to a named human queue with context — never guess silently | M | P2, P3 |
| FR-307 | Agent activity monitoring UI: live runs, queue depth, success/failure rates, cost per work item | S | P5 |

### FR-400 — Knowledge management & RAG

| ID | Requirement | Priority | Personas |
|----|-------------|----------|----------|
| FR-401 | Knowledge corpus ingestion: HMRC manuals/guidance, legislation extracts, OECD guidance, internal tax policies (PDF/DOCX/HTML) with chunking + embeddings + metadata (jurisdiction, tax, date, source authority) | M | P2, P3 |
| FR-402 | Hybrid retrieval (vector + keyword/BM25) with metadata filtering; every generated answer cites sources with links to the exact passage | M | P2, P3 |
| FR-403 | Hallucination controls: answers restricted to retrieved context; explicit "insufficient sources" response path; confidence surfaced | M | P3 |
| FR-404 | Regulatory monitoring: watch configured sources (e.g. HMRC updates), classify relevance per client profile, generate impact assessments into a review queue | S | P1, P3 |
| FR-405 | Knowledge graph of entities/obligations/rules relationships to support multi-hop questions | C | P3 |

### FR-500 — Machine learning & risk analytics

| ID | Requirement | Priority | Personas |
|----|-------------|----------|----------|
| FR-501 | Invoice/AP anomaly detection: duplicates (fuzzy match), unusual amounts/timing, VAT-code misclassification — unsupervised (Isolation Forest + rules) with scored anomaly queue | M | P3 |
| FR-502 | Transaction risk scoring with gradient-boosted model where labels exist; every score accompanied by SHAP-based explanation in the UI | M | P3 |
| FR-503 | Entity resolution / vendor deduplication across sources | S | P3, P5 |
| FR-504 | Cash tax & VAT liability forecasting (time series) with confidence intervals | S | P4 |
| FR-505 | Model registry, versioning, performance monitoring, and drift detection with alerting | S (registry M) | P5 |
| FR-506 | Anomaly disposition workflow: confirm / dismiss with reason; dispositions feed back as labels | M | P3 |

### FR-600 — Reporting & dashboards

| ID | Requirement | Priority | Personas |
|----|-------------|----------|----------|
| FR-601 | Executive dashboard: compliance status heat map, upcoming deadlines, open risk value, ETR/cash-tax KPIs | M | P1, P4 |
| FR-602 | Domain dashboards: VAT analytics, CT analytics, fraud centre, risk centre with drill-down to transaction level | M | P2, P3 |
| FR-603 | Scheduled report generation (PDF/XLSX/PPTX board pack) assembled by the Reporting agent, human-approved before distribution | S | P4 |
| FR-604 | Audit evidence pack export per entity/period/tax: figures, lineage, approvals, agent logs, citations | M | P3 |

### FR-700 — Platform, admin & governance

| ID | Requirement | Priority | Personas |
|----|-------------|----------|----------|
| FR-701 | AuthN/AuthZ: SSO-ready OAuth2/OIDC, JWT sessions, MFA; RBAC with least-privilege roles (admin, preparer, reviewer, approver, read-only, auditor) + entity-scoped ABAC | M | P5 |
| FR-702 | Immutable, append-only audit log of all user and agent actions (who/what/when/before/after), exportable | M | P3, P5 |
| FR-703 | Multi-tenancy with hard tenant isolation (row-level security minimum; schema-per-tenant option for enterprise) | M (architecture) / C (full self-serve) | P6 |
| FR-704 | Admin panel: users, roles, entities, jurisdictions, feature flags, API keys, notification rules | M | P5 |
| FR-705 | Notifications: in-app + email for deadlines, approvals pending, anomalies, pipeline failures | S | all |
| FR-706 | Public REST API (OpenAPI) + webhooks for filed-status/anomaly events | S | P5 |

## 2. Non-functional requirements

| ID | Category | Requirement | Target / acceptance |
|----|----------|-------------|---------------------|
| NFR-01 | Security | All data encrypted in transit (TLS 1.2+) and at rest (AES-256); secrets in vault, never in code/config | Verified by security tests + repo scanning |
| NFR-02 | Security | OWASP ASVS L2 alignment; prompt-injection defences on all LLM inputs (input isolation, output validation, tool allow-lists) | Security test suite passes |
| NFR-03 | Privacy | GDPR: PII detection/classification on ingest, purpose limitation, retention policies, right-to-erasure workflow, EU/UK data residency | DPIA documented; erasure demo |
| NFR-04 | Auditability | 100% of state changes attributable (human or agent+approver) and reconstructible | Audit log completeness tests |
| NFR-05 | Reliability | 99.9% availability target for API tier; graceful degradation when LLM provider unavailable (queue, don't fail) | SLO dashboard; chaos test |
| NFR-06 | Performance | Dashboard p95 < 500 ms (cached aggregates); interactive API p95 < 300 ms; batch pipeline 1M transactions/hour on baseline infra | Load test report (k6/Locust) |
| NFR-07 | AI quality | RAG answers: ≥95% citation-supported claims on evaluation set; deterministic engines: 100% reproducibility | Automated eval harness in CI |
| NFR-08 | AI cost | Cost per work item tracked; budget alerts; model routing (small models for cheap steps) | Cost dashboard |
| NFR-09 | Scalability | Stateless services horizontally scalable; async heavy work via queues; no scale-blocking singletons | Arch review + load test |
| NFR-10 | Maintainability | ≥85% unit coverage on tax engines & services core; typed Python (mypy strict) & TypeScript strict; ADRs for all significant decisions | CI gates |
| NFR-11 | Observability | Structured logs, distributed traces, metrics (RED + agent-specific: tokens, cost, eval scores) with dashboards & alerts | Runbook + dashboards exist |
| NFR-12 | Deployability | One-command local (docker compose); IaC (Terraform) for Azure; blue/green or slot deploys; migrations automated (Alembic) | CD pipeline demo |
| NFR-13 | Accessibility | WCAG 2.1 AA on all frontend pages | axe CI checks |
| NFR-14 | DR/BCP | RPO ≤ 1h, RTO ≤ 4h; automated backups + restore rehearsal documented | Restore runbook tested |
| NFR-15 | Compliance posture | ISO 27001 / SOC 2 control mapping documented (not certified — mapped) | Control matrix doc |

## 3. Explicit non-goals (W — won't do, current horizon)

| ID | Non-goal | Rationale |
|----|----------|-----------|
| W-01 | Direct e-filing to HMRC production APIs | Requires vendor recognition process; MVP produces filing-ready output + (stretch) HMRC MTD sandbox integration |
| W-02 | Full multi-jurisdiction tax content (190 countries) | Content engineering, not architecture; UK depth proves the pattern (FR-206 keeps door open) |
| W-03 | Statutory accounts production / iXBRL tagging | Adjacent product; out of scope |
| W-04 | Autonomous external actions (unsupervised filing, emailing authorities) | Violates GP-1 by design, permanently |
| W-05 | Personal tax / individuals | Enterprise product only |
