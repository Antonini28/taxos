# 05 — Product Roadmap

Four release trains. Each release is demoable, deployed, and documented — no "big bang" at the end. Durations assume a single senior engineer working focused part-time (portfolio reality); an enterprise team would compress the calendar, not the sequence.

## Release train overview

| Release | Theme | Outcome that matters |
|---|---|---|
| **R1 — Foundation & MVP** | "One tax, end-to-end, governed" | UK VAT cycle fully agentic: ingest → validate → compute → anomaly scan → human review → evidence pack, on deployed infrastructure with auth, audit log, and dashboards |
| **R2 — Intelligence** | "The platform gets smart" | Full RAG knowledge base with citations, fraud/risk ML with SHAP, agent chat workspace, CT computation, forecasting |
| **R3 — Enterprise hardening** | "A firm could run clients on this" | Multi-tenancy, ABAC, regulatory monitoring, reporting automation, model monitoring, DR, security test suite, SOC2/ISO mapping |
| **R4 — Scale & polish** | "Portfolio-grade product" | Performance/load evidence, WHT + TP modules, knowledge graph, public API + webhooks, demo environment, marketing site, video |

## R1 — Foundation & MVP

**Epics:** E1 Platform skeleton, E2 Data ingestion & validation, E3 VAT engine, E4 Core agent team, E5 Governance & audit, E6 Core UI

Scope (traceability): FR-101..104, FR-201, FR-204, FR-205, FR-301..304 (301/302/303 minimal viable), FR-501 (rules+IsolationForest), FR-506, FR-601, FR-602 (VAT), FR-604, FR-701, FR-702, FR-704 (minimal), NFR-01/02/04/10/11/12.

Exit criteria (demo script):
1. Upload a quarter of AP/AR/GL data for 3 entities → validation report with quarantined rows.
2. Supervisor agent runs the VAT cycle; VAT agent produces a draft 9-box return with per-box lineage.
3. Fraud agent flags seeded duplicate invoices and VAT-code anomalies; reviewer dispositions one.
4. Reviewer approves the return in the approval queue; audit log shows the full chain.
5. One-click evidence pack (PDF/ZIP) exports.
6. All of the above on Azure, via CI/CD, behind SSO-ready auth.

## R2 — Intelligence

**Epics:** E7 Knowledge platform (RAG), E8 Risk ML & explainability, E9 Agent chat workspace, E10 CT computation, E11 Forecasting

Scope: FR-105 (full), FR-202, FR-401..403, FR-502, FR-503, FR-504, FR-505 (registry+monitoring), FR-305, FR-306 (full), FR-602 (CT+risk), NFR-07/08.

Exit criteria: cited answers on an HMRC-grounded eval set ≥95% support rate; SHAP explanations rendered in anomaly queue; critic-agent loop demonstrably catches a seeded bad draft; CT adjustment schedule reproducible.

## R3 — Enterprise hardening

**Epics:** E12 Multi-tenancy & ABAC, E13 Regulatory monitoring, E14 Reporting automation, E15 SecOps & compliance, E16 Observability & SRE

Scope: FR-404, FR-603, FR-703, FR-705, FR-307, NFR-03/05/09/14/15; security test suite (NFR-02 full), DR rehearsal.

Exit criteria: two demo tenants with provable isolation (tests attempt cross-tenant access and fail); regulatory update triggers an impact assessment in the queue; board pack generated, approved, distributed; restore-from-backup rehearsal documented.

## R4 — Scale & polish

**Epics:** E17 Performance & load evidence, E18 WHT + TP modules, E19 Knowledge graph, E20 Public API & webhooks, E21 Go-to-market assets

Scope: FR-203, FR-207, FR-405, FR-706, FR-106 (one reference connector), NFR-06 evidence; Phase 13 portfolio assets (landing page, demo video, articles, CV bullets).

Exit criteria: k6 load report meeting NFR-06 published; OpenAPI docs live; demo environment with seeded realistic dataset publicly showable; walkthrough video recorded.

## Sequencing rationale (why this order)

1. **Governance before intelligence.** Audit log, approvals, and deterministic computation ship in R1 because they are the trust foundation — retrofitting governance onto an agent platform is how enterprise AI projects die.
2. **One vertical slice first.** VAT is the anchor: highest data volume, clearest rules, best anomaly-detection payoff, most demoable. Depth in one tax proves the pattern for all (mirrors how ONESOURCE and Sightline actually grew).
3. **RAG after data.** A knowledge layer is only credible when it cites; citations are only testable once the eval harness (R2) exists.
4. **Multi-tenancy designed in R1, activated in R3.** Tenant ID is in every table from day one (cheap); self-serve tenancy UX and isolation testing come when there's something worth isolating (expensive).
5. **Performance evidence last.** Optimising before feature-complete wastes effort; NFR targets are designed in from R1 (async, caching, statelessness) and *proven* in R4.

## Risk register (delivery)

| Risk | Impact | Mitigation |
|---|---|---|
| Scope explosion (13-phase brief) | Never ships | Release-train exit criteria are the contract; backlog items outside current train are frozen |
| LLM API cost during development | Budget burn | Local/small models for dev loops; cost tracking from R1 (NFR-08); cached eval fixtures |
| Tax-rule correctness challenged in interviews | Credibility | Rules-as-code with cited HMRC references per rule; honest "illustrative subset" framing in docs |
| Azure cost for always-on demo | Budget burn | Container Apps scale-to-zero; IaC teardown/rebuild scripts; seeded demo data |
