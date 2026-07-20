# 04 — Page Catalogue (remaining estate)

Compact-but-complete specs. Every page inherits: PageHeader pattern, FilterBar where lists exist, URL-as-state, skeleton loading, actionable empty states, problem-details errors, WCAG 2.2 AA, dark/light, responsive rules (§ bottom). Columns: **Purpose / Value** · **Layout & key components** · **States & notes**.

## Auth & shell

| Page | Purpose / value | Layout & components | States & notes |
|---|---|---|---|
| `/login` R1 | SSO entry; zero-friction demo entry locally | Centered card: tenant logo slot, "Continue with Microsoft" (OIDC), dev-issuer persona picker (local only, labelled) | IdP error → problem card with trace; loading = button spinner only |
| `/mfa` R1 | Step-up assurance (IdP-driven) | Status card explaining conditional-access redirect; in-app TOTP fallback form (RHF+Zod) for dev issuer | Lockout state → support path |
| `/settings` R1 | Self-service personalisation | Sections: Profile (read-mostly, IdP-sourced), Appearance (theme/density), Notifications (per-type matrix: in-app/email), Shortcuts sheet | Notification matrix saves optimistically w/ undo toast |

## Dashboards & tax

| Page | Purpose / value | Layout & components | States & notes |
|---|---|---|---|
| `/dashboard/operations` R1 | Analyst landing: "what do I owe today" | Two-column: My work (assigned items w/ SLA chips, escalations addressed to me) · Deadlines (14-day calendar strip) · below: recent batches w/ validation status | Empty = onboarding tasks; everything deep-links |
| `/dashboard/risk` R2 | P3 command centre | KPI row (open exposure, coverage, drift alerts) · risk register table (draft vs confirmed chips) · posture-deterioration feed · heat map by entity×risk-class | Register rows → side-rail RiskAssessmentDraft review (accept/edit/reject agent drafts) |
| `/tax/vat` R1 | VAT compliance workspace | Returns DataTable (entity, period, state, boxes summary, due) → detail = the work-item screen (03 §3.3); analytics tab: box trends by entity (ChartCards), quarantine impact | Detail reuses work-item components — one implementation |
| `/tax/corporate` R2 | CT computation workspace | Computation list → adjustment schedule table (accounting → taxable bridge, per-adjustment CitationChips) + judgement-flag list routed to review | Group-relief flags always render as human-decision cards (never auto) |
| `/tax/withholding` R4 | WHT schedules | Payments table w/ classification chips + treaty-rate column (versioned source noted) · liability schedule export | Classification below threshold = review-needed chip |
| `/tax/calendar` R1 | Deadline control (US-302) | Month/list toggle; obligation cards: entity, type, RAG StatusBadge, owner avatar, state; drag-free (dates are law); ownership reassign inline | RAG transitions animate + notify; heat-map deep-link target |

## AI

| Page | Purpose / value | Layout & components | States & notes |
|---|---|---|---|
| `/agents` R1 | Run observability for users | Runs DataTable (goal, agents, state, cost, duration, initiator) + live strip of executing runs (pulse-live) | Row → run detail (03 §3.2 rail, full-width); filters by state/agent/entity |
| `/agents/monitoring` R2 | P5 estate control (FR-307, ML dashboards) | Tabs: Runs (aggregate charts: success/escalation/cost trends) · Models (estate grid from docs/ml 06 §5: rung, drift, last retrain) · Evals (golden-set score trends per agent) · Providers (circuit state, token spend) | Drift alert rows → drift report detail w/ aggregate-SHAP shift chart |
| `/knowledge` R2 | Cited research (FR-402/403) | Search bar + filters (jurisdiction, tax, as-of date picker) → answer blocks w/ per-claim CitationChips → CitationPanel rail; INSUFFICIENT_SOURCES renders as first-class result card (what was searched, best-match band, [escalate to reviewer]) | History of my questions; copy-with-citations action |
| `/knowledge/regulatory` R3 | Change → impact pipeline (FR-404) | Feed (source, date, DiffView toggle) · impact queue table (relevance verdict, affected entities, urgency) → assessment detail: FACT vs ASSESSMENT sections (visually distinct), implicated pack rules, [accept impact → create work items] [dismiss w/ reason] | Fact quotes always show source diff link |

## Data, documents, work

| Page | Purpose / value | Layout & components | States & notes |
|---|---|---|---|
| `/data/batches` R1 | Ingestion control (US-201) | Upload zone (drag/drop, schema hint per type) · batches DataTable (entity, period, rows, status, control totals) → detail: ValidationReport (rule-level results), quarantine table w/ per-row reasons + [export corrections template] | Dedupe-rejected upload → linked original; progress via WS |
| `/documents` R2 | Library + intake | Intake queue (status chips: pending/review/promoted) · library DataTable w/ type/entity/date filters · bulk upload | Row → Document Review (03 §3.5) |
| `/work` R1 | Pipeline overview | Board (columns = workflow states) / table toggle; work-item cards: type, entity, SLA, assignee, blocked-by chips | Board is read+assign; state changes happen in detail (evidence-first rule) |
| `/reports` R2 | Artifact home (FR-603) | Generated list (type, period, approval state, distribution log) · schedules table (R3) · [generate ▾] wizard (template, scope, period) | Generated reports enter approval flow — state visible; download only post-approval |
| `/audit` R1 | The trust surface (FR-702) | FilterBar (actor incl. agents, action, subject, date) + AuditTrailList (virtualized) · chain-verification status card ("chain verified through #84,112 at 06:00 ✓") · [export slice] | Verification failure = critical banner (links incident runbook); auditor role lands here |

## Admin

| Page | Purpose / value | Layout & components | States & notes |
|---|---|---|---|
| `/admin` R1 | Ops home | Card grid to sub-areas + platform status summary | Role-gated cards |
| `/admin/users` R1 | Access governance | Users DataTable (roles, entity scopes, last active, IdP link) · invite flow · role editor w/ SoD warnings ("user would prepare AND approve for UK-01") | Role changes audited + confirmation; scope editor = entity multi-select w/ search |
| `/admin/entities` R1 | Master data (FR-104) | Entities table → detail: registrations (per-jurisdiction cards), calendars, pack pinning (which pack version this entity computes under, w/ effective dates) | Pack changes create audit + recompute-warning dialog |
| `/admin/api` R4 | Integration surface (FR-706) | Keys table (scopes, last used, rotate) · webhooks (endpoint, events, delivery log w/ retry status, HMAC secret) · usage charts | Delivery failures → replay action |
| `/admin/system` R2 | SRE-lite (NFR-11 for P5) | Cards: queue depths + oldest-age, outbox lag, WS connections, LLM circuit state, error-budget burn charts, integration health; feature-flag table (state, owner, expiry) w/ kill-switch toggles (typed confirmation) | Flag flips audited + annotated on dashboards |

## Responsive behaviour (all pages)

- **Desktop ≥1280:** full layouts as specified; right rail inline.
- **Tablet 768–1279:** nav collapses to icons; right rail becomes overlay sheet; KPI rows wrap 2×2; tables shed tertiary columns (column-priority spec per table).
- **Mobile <768 (monitor-and-approve scope, not data-entry):** bottom tab bar (Dashboard, Work, Approvals, Notifications); tables → card lists; DocViewer/charts render with "best on desktop" affordance where fidelity matters; approvals fully functional (the Partner-in-a-taxi scenario is real).
- Touch targets ≥44px on touch layouts; hover-revealed actions always have a visible menu equivalent.
