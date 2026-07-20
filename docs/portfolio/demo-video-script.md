# Demo Video Script

**Formats:** 3-minute narrated MP4 (landing page, LinkedIn) · 25-second silent GIF (README — scenes 3–6 condensed, captioned).
**Setup:** `just demo` (demo seed, stub-LLM — deterministic, no waiting on providers), dark theme, 1920×1080, cursor highlighting on, notifications off. Screen-record per scene; VO recorded separately against the timings.

| # | Time | Screen | Voice-over |
|---|---|---|---|
| 1 | 0:00–0:15 | Executive dashboard, slow pan across heat map and KPIs | "This is TaxOS — an agentic AI platform for enterprise tax compliance. Everything you'll see is governed by one rule: agents prepare the work; humans approve it." |
| 2 | 0:15–0:35 | Data → Ingestion: drag CSV, validation report appears, click into quarantine (12 rows, rule reasons) | "It starts with data. ERP extracts are validated row by row — failures are quarantined with the exact rule they broke, and nothing unvalidated ever reaches a computation." |
| 3 | 0:35–1:10 | Agent workspace: type `/prepare VAT UK-01 2026-Q2`; plan card appears; timeline lights up; pause on the escalation card; click Upload, run resumes | "Now the agent team. The Supervisor builds a plan — data readiness, computation, anomaly review, reporting. Watch what happens when something's missing: the run doesn't guess. It parks, asks for the payroll extract, and resumes exactly where it stopped." |
| 4 | 1:10–1:40 | Draft card: 9-box return; click Box 4 → LineageSheet slides in; click a citation chip → HMRC passage panel | "The return itself is computed by a deterministic rule engine — the AI never does the maths. Every box drills down to its source transactions. Every claim in the narrative cites the HMRC guidance it relies on — click it, read the passage." |
| 5 | 1:40–2:10 | Fraud centre: case queue; open duplicate case; SHAP-style explanation; disposition with reason code | "While the return was being prepared, the anomaly pipeline flagged these — a near-duplicate invoice pair, explained in plain language: same supplier, amounts within two percent, four days apart. The reviewer's decision is recorded — and becomes training data." |
| 6 | 2:10–2:40 | Work item: state bar, approval card with content hash; approve → confirmation; audit trail with agent + human entries; export evidence pack, flash the PDF | "Review is evidence-first. Approval binds to a fingerprint of exactly what was reviewed — change the data, and the approval voids. And this is the payoff: one click assembles the evidence pack. Figures, lineage, approvals, agent traces, citations. The enquiry response that used to take weeks." |
| 7 | 2:40–3:00 | Back to executive dashboard; cut to architecture diagram; end card | "Deterministic where it must be. Intelligent where it helps. Auditable everywhere. TaxOS — the repo, the architecture, and eighteen design decisions are linked below." |

**End card:** wordmark · `github.com/Antonini28/taxos` · "Agents prepare. Humans decide. Everything is evidence."
**GIF cut:** scenes 3→6 key moments, caption bar instead of VO, loop-friendly (ends on dashboard).
**Production notes:** no scene longer than 35s without a click; VO ~140 wpm; captions burned in (LinkedIn autoplays muted); retakes are cheap because the demo is deterministic — record until every cursor movement is intentional.
