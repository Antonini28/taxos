# Phase 3 — AI Architecture

**Product:** Enterprise Agentic Tax Operating System (TaxOS)
**Status:** Complete — awaiting stakeholder review
**Inputs:** Phase 1 (FR-3xx agent requirements), Phase 2 (ADR-012 agent-runtime isolation, Tool Gateway, envelope contract), principles AP-1..AP-5
**Last updated:** 2026-07-20

## Document map

| # | Document | Contents |
|---|----------|----------|
| 01 | [Framework Evaluation](01-framework-evaluation.md) | LangGraph vs CrewAI vs AutoGen: criteria, scoring, recommendation (→ ADR-013) |
| 02 | [Agent System Design](02-agent-system-design.md) | Orchestration graph, run lifecycle, memory architecture, model routing, error taxonomy, HITL mechanics |
| 03 | [Core Agent Catalogue (MVP)](03-core-agents.md) | Full specifications: Supervisor, Data, VAT, Fraud, Reporting, Critic |
| 04 | [Extended Agent Catalogue (R2–R4)](04-extended-agents.md) | Research, Document, Corporate Tax, Risk, Regulatory Monitor, Audit Readiness, Financial Statement + the TaxDomainAgent template (WHT/Payroll/TP/Indirect) |
| 05 | [Agent Evaluation Framework](05-agent-evaluation.md) | Offline evals, golden datasets, LLM-as-judge rubrics, CI gates, online quality monitoring |
| — | [ADR-013](../architecture/adr/ADR-013-langgraph.md) | Agent framework selection record |

## How the brief's 24 example agents map to this roster

A principal-engineer decision up front: several items on the example agent list are **platform functions, not LLM agents** — giving them prompts would be architecture theatre. The mapping is explicit and every capability is accounted for:

| Brief item | Realised as | Where |
|---|---|---|
| Supervisor, Planning, Workflow Coordinator | **Supervisor agent** (plans are bounded graphs; workflow state lives in the workflow module) | 03 |
| Reflection, Critic | **Critic agent** (one rubric-driven reviewer; "reflection" is its revise loop) | 03 |
| Memory Agent | **Memory subsystem** — deterministic storage tiers, not an agent (an LLM deciding what to remember is an audit hazard) | 02 §3 |
| Human Approval Agent | **Workflow approval gate** — humans approve; software routes (GP-1 forbids an "approval agent" by definition) | Phase 2, doc 10 |
| Tax Data Engineer | **Data agent** | 03 |
| VAT Agent | **VAT agent** (first instance of the TaxDomainAgent template) | 03 |
| Fraud Detection | **Fraud agent** (fronts the deterministic ML pipeline — the models detect; the agent investigates and narrates) | 03 |
| Executive Reporting | **Reporting agent** | 03 |
| Knowledge Retrieval, Research | **Research agent** (retrieval is a tool; research is the agent using it) | 04 |
| Document Processing | **Document agent** | 04 |
| Corporate Tax, Financial Statement | **Corporate Tax agent** + **Financial Statement agent** (CT's upstream) | 04 |
| Risk Assessment | **Risk agent** | 04 |
| Compliance Monitoring, Regulatory Monitoring | **Regulatory Monitor agent** | 04 |
| Audit Readiness | **Audit Readiness agent** | 04 |
| Withholding Tax, Payroll Tax, Indirect Tax, Transfer Pricing | **TaxDomainAgent template** instances — same agent shape, different content pack + tool grants (AP-3 applied to agents) | 04 |

Result: **13 LLM agents + 1 template**, each with the full required specification (purpose, responsibilities, tools, memory, prompt, inputs, outputs, error handling, escalation, evaluation metrics), rather than 24 overlapping name-plates.
