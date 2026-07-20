# TaxOS User Manual

Organised by what you're trying to do, then by role. Screens referenced by name; navigation: left sidebar groups, ⌘K to jump anywhere, `?` for shortcuts.

## 1. First session (all roles)

Sign in with your organisation account (SSO + MFA). Your landing page matches your role — Analysts see their work queue, reviewers their approvals, executives the group dashboard. The **entity-scope chip** (top left) always shows whose data you're viewing; the **as-of chip** on any dashboard shows data freshness. Anything you can click through to — a figure, a flag, a status — leads to its evidence.

## 2. Preparing compliance (Analyst / Tax Ops)

**Upload data:** *Data → Ingestion* → drag your extract → validation runs automatically. Green = validated; amber = validated with exceptions (open the report; quarantined rows show the exact rule each failed — fix at source and re-upload, or export the corrections template). A duplicate file is rejected and linked to the original.

**Run the agent team:** *AI → Workspace* → type or pick `/prepare VAT UK-01 2026-Q2`. You'll see the Supervisor's plan, then live progress per agent. If something's missing (e.g. payroll extract), the run **parks** with an escalation card telling you exactly what to provide — it resumes where it left off, nothing recomputes. The run always ends at *awaiting review* — agents cannot approve or file.

**Read a draft return:** boxes come from the deterministic engine (every value drills to its source transactions); the narrative explains variances with citations — chips like `VIT13500` open the exact HMRC passage. **Unexplained variance flagged** is honest and normal; invented explanations are what the system refuses to do.

## 3. Reviewing & approving (Manager / Reviewer)

*Work → My Approvals* — items with SLA chips, oldest first. Open one: check the state bar, read the narrative, drill any figure via **lineage** (the sum of contributing transactions always equals the figure — click it), check linked anomalies and the Critic's verdict. Then **Approve** (restates scope + content fingerprint — what you approve is exactly what you saw) or **Request changes** (comment required, routes back). If the button is disabled, the reason is written under it (e.g. you prepared this item — segregation of duties). If data changed since preparation, the item reverts to draft and any approval is void — you'll see that in the trail.

## 4. Investigating anomalies (Risk / Fraud)

*Risk & Fraud → Fraud Centre.* The queue is ranked by materiality × score within your review capacity. Open a case: the **why** is first — plain-language contributions ("amount is 4.2× this vendor's typical invoice"), model version noted; then the transactions, vendor history, and any prior dispositions of the same pattern. Disposition with a **reason code** — reasons matter: they teach the models and tune future queues. "Scan failed" and "no anomalies" are different states — the platform never conflates them.

## 5. Research (any tax role)

*Knowledge → Search.* Ask in plain language; set the **as-of date** if your question is about a past period. Every claim is cited — hover a chip for the quoted passage, its source and validity window. If sources conflict, you'll see both, ranked by authority (legislation over guidance over policy) — the platform surfaces conflicts, it doesn't resolve them. **"Insufficient sources"** is a real answer meaning the corpus can't support a grounded response; use *escalate* to route the question to a colleague.

## 6. Executive view (Director / CFO / Partner)

*Dashboard.* Five-second read: compliance heat map (entity × obligation, RAG), deadlines, open exposure, cash-tax trend with forecast band (intervals are calibrated; assumptions visible). Everything drills down — the board question "why is that red?" is two clicks, not an email. *Export* gives a board-paste snapshot or PDF pack. Partners: the tenant switcher (top left) is the client boundary — visual framing changes with it so you always know whose data is on screen.

## 7. Administration (System Administrator)

*Admin.* Users & roles (SoD warnings appear if a role combination would let someone prepare *and* approve the same scope) · entities & registrations (including which rule-pack version each entity computes under) · system health (queues, integrations, AI provider state, kill switches — flipping one requires typed confirmation and is audited) · model monitoring (which detectors are active per entity, drift status, evaluation trends).

## 8. Audit & evidence (Auditor / Risk)

*Audit* shows every action — human and agent — with actor, timestamp, and before/after, protected by a cryptographic chain whose verification status is displayed. *Evidence pack* (on any approved item) exports the complete story: figures, lineage, approvals, agent traces, citations — the enquiry response that used to take weeks.

## 9. Notifications & personal settings

*Settings → Notifications*: per-type matrix (in-app/email) for deadlines, approvals waiting, escalations, anomalies. Theme (light/dark/system), density (comfortable/dense), and keyboard shortcuts are per-user. Deadlines escalate amber → red automatically (7 → 3 days by default; admins configure).

## 10. When something looks wrong

Every error shows a reference id — include it when contacting support (it links directly to the technical trace). Amber banners mean degraded-but-safe (e.g. AI provider down: runs park and resume; nothing is lost). If a figure looks wrong, **drill its lineage before anything else** — the answer is usually in the contributing rows, and if it isn't, that lineage view is exactly what support needs.
