# 02 — Information Architecture

## 1. Sitemap (28 screens, release-tagged)

```
/login                              R1   OIDC redirect + dev-issuer picker (local)
/mfa                                R1   step-up prompt (IdP-driven; in-app fallback screen)

/ (role-based landing → one of the dashboards below)

DASHBOARDS
/dashboard                          R1   Executive Dashboard (P1/P4; Partner view)
/dashboard/risk                     R2   Risk Intelligence Centre (P3)
/dashboard/operations               R1   Operations home (P2 landing: my queue, deadlines)

TAX
/tax/vat                            R1   VAT Analysis (returns list → detail → boxes → lineage)
/tax/corporate                      R2   Corporate Tax Analysis
/tax/withholding                    R4   Withholding Tax Analysis
/tax/calendar                       R1   Compliance Calendar (obligations, RAG, ownership)

AI
/agents                             R1   Agent Activity (runs list, live + history)
/agents/runs/[id]                   R1   Run detail (AgentTimeline, traces, cost)
/agents/workspace                   R1   AI Agent Chat Workspace (instruct + steer + escalations)
/agents/monitoring                  R2   AI Model Monitoring (estate grid, drift, evals) [admin]

RISK & FRAUD
/fraud                              R1   Fraud Detection Centre (anomaly queue, cases)
/fraud/cases/[id]                   R1   Case detail (SHAP, context, disposition)
/risk/register                      R2   Risk register (P3 drafts→confirmed)

DATA & DOCUMENTS
/data/batches                       R1   Ingestion (upload, validation reports, quarantine)
/documents                          R2   Document Management (library, intake queue)
/documents/[id]                     R2   Document Review (flagship, doc 03 §5)

KNOWLEDGE
/knowledge                          R2   Knowledge Search (research Q&A with citations)
/knowledge/regulatory              R3   Regulatory Updates (change feed, impact queue)

WORK
/work                               R1   Workflow Management (work items, pipelines, queues)
/work/items/[id]                    R1   Work item detail (state bar, evidence, approval)
/work/approvals                     R1   My Approvals (the approver's queue)
/reports                            R2   Reports Centre (generated artifacts, schedules)
/audit                              R1   Audit & Activity Logs (chain-verified trail)

ADMIN
/admin                              R1   Administration home
/admin/users                        R1   Users & roles
/admin/entities                     R1   Entities & jurisdictions (master data)
/admin/api                          R4   API Management (keys, webhooks, usage)
/admin/system                       R2   System Health (queues, SLOs, integrations)
/settings                           R1   Profile, notifications, density/theme, shortcuts
```

## 2. Navigation model

- **Left nav (persistent, collapsible):** 7 groups exactly as the sitemap sections above — Dashboards, Tax, AI, Risk & Fraud, Data & Documents, Knowledge, Work (+ Admin for authorized roles). Icons + labels; collapsed = icons + tooltips; active trail highlighted; badge counts on Work/Approvals and Fraud (live via WS).
- **Top bar:** tenant/entity scope switcher (left, always visible — the "whose data" anchor), breadcrumbs are *not* here (they live in PageHeader), global search/⌘K, notification bell, help (`?`), user menu (theme, density, profile).
- **Right context rail (360px, contextual):** the detail companion — LineageSheet, CitationPanel, run step detail, approval card. One rail, consistent position, so "details appear on the right" becomes muscle memory.
- **URL is state:** every filter, table view, tab, and selected entity serialises to the URL (shareable deep links — "look at this anomaly" is a paste, not a screenshot + directions). Back/forward always works.
- **Escape hatches:** every entity chip anywhere (entity, batch, computation, run, anomaly) is a link to its home screen — the graph of screens is navigable from any node (D2).

## 3. Role-based experiences (D5)

RBAC (Phase 2) controls *access*; the design controls *emphasis*. Mapping platform roles → the stakeholder's role language:

| Role (stakeholder terms) | Platform role | Landing | Nav emphasis | Density default | Signature needs |
|---|---|---|---|---|---|
| Analyst | PREPARER | /dashboard/operations | Work, Data, Tax | Dense | My queue, upload, batch status, escalations addressed to me |
| Manager | REVIEWER | /work/approvals | Work, Fraud, Tax | Dense | Approval queue with evidence one click away; SoD-explained disabled states |
| Director (Head of Tax) | APPROVER + org scope | /dashboard | Dashboards, Risk | Comfortable | Compliance heat map, exposure, deadline risk, agent activity summary |
| Partner (P6 engagement view) | APPROVER multi-tenant | /dashboard (tenant-switcher prominent) | Dashboards, Reports | Comfortable | Cross-client posture, white-label report readiness, isolation cues |
| System Administrator | ADMIN | /admin/system | Admin, AI monitoring | Dense | Health, queues, model estate, users, flags |
| Auditor | AUDITOR | /audit | Audit, Work (read) | Dense | Chain verification, evidence packs, read-everything-change-nothing UI (all mutating affordances absent, not disabled) |

## 4. Dashboard hierarchy (three altitudes, consistent drill physics)

```
L1  Executive Dashboard        "Is the group healthy?"     — KPIs, heat map, exposure, trendlines
      ↓ click any KPI/cell
L2  Domain dashboards          "Where and why?"            — VAT / Risk / Fraud / Operations:
      (filtered analytics)       charts + FilterBar + DataTable of underlying population
      ↓ click any row/mark
L3  Record detail              "Show me the evidence."     — work item / computation / case /
      (+ right rail)             document with lineage, citations, audit trail, actions
```

One rule: **every altitude change preserves filter context** (period, entity scope travel with the click). L1 answers in 5 seconds, L2 in 5 clicks, L3 is where work happens. Export exists at every altitude (PNG/CSV at L2 charts/tables, evidence pack at L3).

## 5. Cross-cutting screen patterns (defined once, reused everywhere)

| Pattern | Definition |
|---|---|
| **List → Detail** | L2 lists are DataTable + FilterBar + saved views; row click → L3 route (not modal — L3s are shareable URLs); bulk actions on selection where domain allows |
| **State-machine screens** | Any stateful record (work item, batch, run, case) leads with `WorkflowStateBar` + permitted-actions row derived from state × role — the UI never offers an illegal transition (server still enforces) |
| **Freshness** | Every aggregate-driven region shows `as_of` chip; stale (> policy) escalates to a visible banner (D3) |
| **Live regions** | WS-driven updates animate in via `expand`, announce via `aria-live`; lists never reorder under the pointer (new items batch behind a "3 new — show" pill) |
| **Empty states** | Always actionable: first-run empties teach ("No batches yet — upload your first extract"), filtered empties offer to clear filters |
| **Error states** | Problem-details rendered with trace_id + retry; degraded modes (LLM circuit open, stub mode) get persistent amber banners, not toasts |
| **Loading** | Skeletons that reserve exact final space (zero CLS); table skeletons show column structure; never spinners on full pages |
