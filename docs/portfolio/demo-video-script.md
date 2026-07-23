# Demo Video Script

**Formats:** ~3¼-minute narrated MP4 (landing page, LinkedIn, README link) · 25-second silent GIF (README — scenes 4, 5, 8 condensed, captioned).
**Setup:** `just demo` first (deterministic seed + both agent cycles, stub-LLM — no waiting on providers), light theme for screens / dark for the opening dashboard, 1920×1080, cursor highlighting on, notifications off. Screen-record per scene; VO recorded separately against the timings.
**Status:** refreshed 2026-07-23 against the shipped UI — every screen direction below was verified live. No scene shows anything that doesn't exist.

| # | Time | Screen | Voice-over |
|---|---|---|---|
| 1 | 0:00–0:12 | Executive dashboard (dark), slow pan across KPIs | "This is TaxOS — an agentic AI platform for enterprise tax compliance, built on one rule: agents prepare the work; humans approve it." |
| 2 | 0:12–0:30 | Terminal: `just demo` scrolling — seed, agent steps printing, "refused — you prepared this item", chain verified | "One command runs the whole story locally — no cloud, no API keys. Watch the log: the agents prepare a VAT return and a Corporation Tax computation, and when the preparer tries to approve their own work, the platform refuses them by name." |
| 3 | 0:30–0:50 | Agents screen: open the VAT run — step timeline (data → vat → fraud → reporting), pause on a step showing tools called + "DETERMINISTIC" confidence basis | "Every agent step is on the record — the goal, the tools it called, its confidence *and the basis for it*. This run ends the only way a run can end: handed off to a human. There is no code path from an agent to an approval." |
| 4 | 0:50–1:20 | VAT return: click Box 4 → lineage table slides open — invoices, treatments, citation refs, green "reconciles" | "The return comes from a deterministic rule engine — the AI never does the maths. Click any box and the invoices behind it appear, each carrying the HMRC reference that authorises its treatment. The contributions reconcile to the box exactly — the screen shows it rather than asserting it." |
| 5 | 1:20–1:45 | Corporation Tax screen: pan the computation (PBT → add-backs → reliefs → TTP → charge), open Add-backs lineage — CTA 2009 citations | "And here's the claim that makes this a platform, proven: Corporation Tax runs through the *same* engine, the same lineage, the same approval gate — everything tax-specific lives in a rule pack. Adding this tax type changed no engine code." |
| 6 | 1:45–2:15 | Fraud centre: anomaly queue (duplicate explained in plain language) → scroll to Model risk score with Shapley bars → the Rung-3 "Not yet trained · INSUFFICIENT_LABELS" card | "Risk runs a ladder. Explainable rules first — a duplicate named against its twin. Then a statistical model where every score carries an exact Shapley explanation — the bars sum to the score. And above it, a supervised model that learns from reviewers' decisions — and *refuses to train* until it has enough real labels. It says so, with the counts. Refusing to pretend is the feature." |
| 7 | 2:15–2:35 | Knowledge screen: click the reverse-charge example → cited passages; then the German corporation-tax example → "Insufficient sources" card | "Research works the same way. Ask a question and the answer *is* the cited evidence — legislation ranked above guidance. Ask something the corpus can't support, and it tells you exactly that, with what it searched — never an improvised answer." |
| 8 | 2:35–3:05 | Approvals: CT item as Preparer — button disabled under "You prepared this item — a second reviewer is required"; switch seat to Reviewer, approve; click Export evidence pack, flash the rendered document (boxes, lineage, approval hash, chain-verified banner) | "Review is evidence-first. As the preparer, approval is refused — by name. A second reviewer approves, bound to a hash of exactly what they read. And the payoff: one click assembles the evidence pack — figures, lineage, the approval, the agent trace, and a fresh audit-chain verification. The enquiry response that used to take weeks." |
| 9 | 3:05–3:20 | Filing calendar (Q1 overdue in red, Q2 + CT awaiting review) → cut to end card | "Every obligation, its statutory deadline, and where it stands — derived from live state, so the calendar can't disagree with the approvals queue. Deterministic where it must be. Intelligent where it helps. Honest everywhere. TaxOS — repo linked below." |

**End card:** wordmark · `github.com/Antonini28/taxos` · "Agents prepare. Humans decide. Everything is evidence." · "169 tests · 18 ADRs · no API keys"

**GIF cut (README, 25s):** scene 4 (Box 4 lineage opens, "reconciles") → scene 5 (CT computation) → scene 8 (approval refused → approved → evidence pack). Caption bar instead of VO; loop-friendly (ends on the evidence pack banner).

**Production notes:**
- No scene longer than 35s without a click; VO ~140 wpm; captions burned in (LinkedIn autoplays muted).
- Retakes are cheap — the demo is deterministic, so record until every cursor movement is intentional.
- Scene 2's terminal beat is the trust anchor: it proves the thing runs, not just screenshots. Keep the "refused — you prepared this item" line on screen for a full second.
- Scene 6 is the differentiator most viewers won't have seen anywhere: linger on the INSUFFICIENT_LABELS card long enough to read its first line.
- Before recording: `just demo` (fresh reset), approve nothing manually beforehand except what scene 8 does on camera — the CT item must still be AWAITING_REVIEW when scene 8 starts.
