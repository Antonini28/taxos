# 03 — Flagship Screen Specifications

Five screens carry the product's reputation. Each spec: journey → wireframe → components → states → interactions → accessibility notes. Wireframes are structural (grid regions), not pixel art — the design system (doc 01) supplies the pixels.

---

## 3.1 Executive Dashboard (`/dashboard`) — R1

**Journey:** Marcus (CFO) or Amara (Head of Tax) opens Monday morning. In 5 seconds: are we compliant, what's at risk, what needs me. In 2 clicks: the evidence behind any number. Exports a board-ready view.

```
┌─ PageHeader: "Group Tax Overview" · entity-scope chip · as_of chip · [Export ▾] ─┐
├──────────────────────────────────────────────────────────────────────────────────┤
│ KpiTile row (4):                                                                 │
│ [Compliance health   ] [Open exposure     ] [Cash tax forecast ] [Agent hours    │
│  47/49 obligations on   £1.24m across 12     Q3: £8.2m ±0.6m      saved MTD: 312 │
│  track · ▲2 vs last Q   open items · ▼18%    sparkline 6Q         ▲41% vs plan  ]│
├──────────────────────────────────────────────────────────────────────────────────┤
│ ┌ Compliance heat map (⅔ width) ────────────┐ ┌ Needs attention (⅓) ───────────┐ │
│ │ entities × obligation types grid;         │ │ ranked action list:            │ │
│ │ cells = StatusBadge (RAG); click →        │ │ · RED: UK-03 VAT due 3d, draft │ │
│ │ /tax/calendar filtered to cell            │ │ · 2 approvals waiting on you   │ │
│ │                                           │ │ · HIGH anomaly case £84k       │ │
│ │                                           │ │ · reg. change: 4 entities hit  │ │
│ └───────────────────────────────────────────┘ └────────── each row deep-links ─┘ │
├──────────────────────────────────────────────────────────────────────────────────┤
│ ┌ Liability trend (½) ──────────┐ ┌ ETR bridge (¼) ──┐ ┌ Anomaly value (¼) ────┐ │
│ │ line: VAT/CT liability by     │ │ waterfall:       │ │ stacked bar by status  │ │
│ │ quarter, forecast band dashed │ │ statutory→ETR    │ │ open/confirmed/       │ │
│ │ (series 1/2; one axis)        │ │                  │ │ dismissed by month     │ │
│ └───────────────────────────────┘ └──────────────────┘ └────────────────────────┘ │
├─ Agent activity strip: 3 runs today · 2 AWAITING_REVIEW · cost £4.12 · [→ /agents]┤
└──────────────────────────────────────────────────────────────────────────────────┘
```

**Components:** KpiTile×4, heat map (custom grid of StatusBadge cells), action list, ChartCard×3, activity strip. All ChartCards: table-view toggle + export.
**States:** Loading = skeleton grid mirroring exact layout; Empty (new tenant) = onboarding checklist replacing heat map ("Connect data → first computation → first review"); Degraded = amber `as_of` banner when aggregates stale; Error per-card (one failed aggregate never blanks the page — card-level ErrorState with retry).
**Interactions:** every KPI → L2 with filters carried; heat-map cell → calendar filtered; period switcher in FilterBar affects all cards atomically (single URL param); `Export ▾` = PNG snapshot (board paste) / PDF pack / schedule report (R3 → Reports Centre).
**A11y:** heat map = table semantics (`role=grid`, row/col headers announced); KPI deltas have text equivalents ("up two obligations vs last quarter"); charts have `aria-describedby` summaries.

---

## 3.2 AI Agent Workspace (`/agents/workspace` + `/agents/runs/[id]`) — R1

**Journey:** Daniel instructs "Prepare Q2 VAT for UK-01". Watches the plan appear, steps light up, VAT draft lands with citations; an escalation card asks for the payroll file; he uploads, run resumes; ends AWAITING_HUMAN_REVIEW with a handoff card → one click to the work item. Priya later replays the whole run from the trace.

```
┌ Workspace ───────────────────────────────────────────────────────────────────────┐
│ ┌ Conversation (⅗) ─────────────────────────┐ ┌ Run rail (⅖) ──────────────────┐ │
│ │ [user] Prepare Q2 VAT for UK-01           │ │ AgentTimeline                  │ │
│ │ [supervisor] Plan (4 steps) ── approve?   │ │  ● Data readiness      12s ✓   │ │
│ │   (plan card: steps, agents, budget)      │ │  ● VAT computation     4s  ✓   │ │
│ │ [data-agent] Readiness: GAPS ──────────── │ │  ◐ Anomaly review      live…   │ │
│ │   EscalationCard: payroll extract missing │ │  ○ Reporting           queued  │ │
│ │   [Upload file] [Reassign] [Cancel run]   │ │ per step: agent chip, model,   │ │
│ │ [vat-agent] Draft ready ────────────────  │ │ tokens, £cost, duration        │ │
│ │   DraftCard: boxes ref, variance summary, │ │ ── click step → step detail:   │ │
│ │   CitationChips, ConfidenceIndicator      │ │ reasoning trace, tool calls    │ │
│ │   (GROUNDED 94%)                          │ │ (req/resp), envelope, budget   │ │
│ │ [system] Run → AWAITING_HUMAN_REVIEW      │ │ meter                          │ │
│ │   HandoffCard → /work/items/1482          │ │                                │ │
│ │ [input: instruct or steer… ] [/commands]  │ │ Cost: £0.87 / budget £5.00     │ │
│ └───────────────────────────────────────────┘ └────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────────┘
```

**Design decisions:** conversation ≠ chat toy — every agent message is a **typed card** (PlanCard, EscalationCard, DraftCard, HandoffCard) with actions, not prose blobs (D4); the run rail is the *same component* as `/agents/runs/[id]` (history = live view, replayed); reasoning traces are collapsed by default, one click to expand, always available (never truncated away — FR-302); confidence always shows basis; **no approval actions exist here** — HandoffCards route to the work item where ApprovalCard lives (the UI mirrors the architectural gate, ADR-012).
**States:** streaming (typed cards build progressively, `pulse-live` on active step); WAITING_INPUT (escalation pinned, run dimmed but resumable); WAITING_PROVIDER (amber banner "AI provider degraded — run parked, will resume"); FAILED (full trace preserved + "escalated to X" record); stub mode (persistent watermark chip).
**Interactions:** slash commands (`/prepare`, `/explain box 4`, `/status`); steering messages mid-run (labelled "will be considered at next planning step" — honest about mechanics); Esc never kills a run (explicit Cancel with confirmation); WS-driven, polling fallback.
**A11y:** run updates via `aria-live=polite` ("VAT computation completed"); timeline keyboard-navigable (roving tabindex); cards are landmarks with labelled regions; cost meter has text value.

---

## 3.3 Approvals & Work Item Detail (`/work/approvals`, `/work/items/[id]`) — R1

**Journey:** Priya opens her queue: 4 items, oldest first, SLA chips. Opens the VAT return item: state bar shows Prepared→Review; she reads the variance narrative, opens LineageSheet on Box 4, checks the two anomaly flags (one already dispositioned), sees the Critic passed with 0 findings, approves with comment — identity, hash, and timestamp recorded, item locks.

```
┌ /work/items/1482 ────────────────────────────────────────────────────────────────┐
│ PageHeader: "UK-01 · VAT Q2-2026" · WorkflowStateBar: ✓Draft ✓Prepared ●Review ○Approved
├──────────────────────────────────────────────────────────────────────────────────┤
│ ┌ Main (⅔) ────────────────────────────────┐ ┌ Right rail (⅓) ─────────────────┐ │
│ │ Tabs: Return · Narrative · Anomalies ·   │ │ ApprovalCard                    │ │
│ │       Documents · Audit trail            │ │  content hash: a3f2…e9 ⧉        │ │
│ │ [Return] 9-box table; every value →      │ │  prepared by: agent run #r-311  │ │
│ │  LineageSheet (right rail takeover)      │ │   (approved plan by daniel@)    │ │
│ │ [Narrative] variance analysis w/         │ │  critic: PASS (0 findings) →    │ │
│ │  CitationChips inline; ConfidenceBadge   │ │  SoD: ✓ you may approve         │ │
│ │ [Anomalies] 2 linked flags w/ status     │ │  [Approve…] [Request changes]   │ │
│ │ [Audit trail] AuditTrailList (verified ✓)│ │  comment (required on both)     │ │
│ └──────────────────────────────────────────┘ └─────────────────────────────────┘ │
```

**Design decisions:** the approval action lives **with the evidence**, not in a list (approving from the queue row is deliberately impossible — evidence-first approval is the product's ethic in pixels); disabled approve states always explain (SoD: "You prepared this item — a second reviewer is required", stale: "Content changed since you opened this — refresh"); Approve opens a confirmation restating scope + hash — the legal moment is unmistakable; request-changes routes back with required comment → preparer notification.
**Queue screen:** DataTable (SLA countdown chips, prepared-by, materiality, age), saved views ("VAT only", "high materiality"), bulk *assign* (never bulk approve — one evidence view per approval, by design).
**States:** post-approval the item renders locked (read-only, green state bar, evidence-pack button promoted); voided approval (content changed later) shows the void event prominently in trail with the hash mismatch.
**A11y:** state bar = `aria-current` step pattern; approval dialog focus-trapped with explicit labelled destructive/affirmative buttons; hash truncation has copy-full affordance.

---

## 3.4 Fraud & Risk Centre (`/fraud`, `/fraud/cases/[id]`) — R1

**Journey:** Priya triages: queue sorted by materiality × score; opens a duplicate-pair case; sees SHAP-style component explanation ("same supplier, amounts within 1.8%, 4 days apart"), side-by-side invoice fields with differences highlighted, vendor history ("2 prior confirmed duplicates"); dispositions CONFIRMED with reason → label recorded, recovery task spawned.

```
┌ /fraud ──────────────────────────────────────────────────────────────────────────┐
│ KpiTile row: Open cases 23 · Open value £412k · Confirm rate 34% · Median TTd 2.1d
│ FilterBar: severity · type · entity · period · [saved views]                     │
│ ┌ Case queue (⅗ DataTable) ──────────────┐ ┌ Preview rail (⅖) ─────────────────┐ │
│ │ severity·type·entities·value·age·score │ │ AnomalyCaseCard for selected row: │ │
│ │ rows keyboard-navigable, j/k           │ │ pattern summary · ShapBar ·       │ │
│ │                                        │ │ prior dispositions · [Open case]  │ │
│ └────────────────────────────────────────┘ └───────────────────────────────────┘ │
Case detail: evidence tabs (Explanation · Transactions · Vendor history · Related cases)
+ disposition footer: [Confirm ▾ reason] [Dismiss ▾ reason] [Assign] [Add note]
```

**Design decisions:** explanation is the hero — ShapBar with plain-language feature labels renders *before* transaction tables (reviewers decide on "why flagged", D4); reason codes are required, structured (the ML label pipeline runs through this select — doc/ml 01 §2 made UI); disposition is server-confirmed with visible pending state (audited action); model-version footnote on every explanation ("scored by if-uk01-ap@2026.06 · rules v1.4").
**States:** queue empty = green celebratory-calm state ("No open cases — last scan 14:02, 0 flags"); scan-failed banner distinct from "no anomalies" (never conflate — doc/ai 03 §3.4's invariant, in pixels); case already dispositioned elsewhere → stale banner + refresh (no lost work: note draft preserved).
**A11y:** j/k roving with `aria-activedescendant`; ShapBar has table alternative; severity always icon+text.

---

## 3.5 Document Review (`/documents/[id]`) — R2

**Journey:** an invoice lands in intake; Daniel opens review: PDF left, extracted fields right with per-field confidence; two low-confidence fields flagged; clicking a field highlights its source region on the page (and vice-versa); one field disagrees with master data (VAT number checksum) — shown as validation flag with suggested vendor match; he corrects, confirms, promotes to staging; version history records the correction (→ future training label).

```
┌ /documents/8812 ─────────────────────────────────────────────────────────────────┐
│ PageHeader: invoice_8812.pdf · vendor guess: "Apex Supplies Ltd (92%)" · [Actions]
│ ┌ DocViewer (⅗) ─────────────────────────┐ ┌ Extraction rail (⅖) ──────────────┐ │
│ │ page render + bounding-box overlays;   │ │ Tabs: Fields · Issues · History   │ │
│ │ overlay ↔ field two-way highlight;     │ │ [Fields] each: value · confidence │ │
│ │ zoom/fit/rotate; page thumbnails       │ │  chip · source-region link ·      │ │
│ │                                        │ │  [✓ accept] [✎ correct]           │ │
│ │                                        │ │  low-confidence sorted first      │ │
│ │                                        │ │ [Issues] validation flags w/      │ │
│ │                                        │ │  evidence links (master data,     │ │
│ │                                        │ │  duplicate check, VAT format)     │ │
│ │                                        │ │ [History] versions + who/what     │ │
│ └────────────────────────────────────────┘ └───────── footer: [Reject] [Promote]┘ │
```

**Design decisions:** absent-is-absent rendered honestly (missing fields show "not present in document", never blank inputs inviting invention — the Document agent's contract, in UI); corrections require selecting the source region *or* ticking "not in document" (provenance discipline for the training loop); AI recommendations (vendor match, tax-code suggestion) are visually distinct proposal chips requiring explicit accept; Promote is disabled until all low-confidence fields are resolved — with the count as the button label ("Resolve 2 fields to promote").
**States:** OCR-degraded (scan quality banner + "manual entry mode"); duplicate-suspect (prominent linked-case banner before any promote); bulk intake queue view with per-doc status chips.
**A11y:** overlays keyboard-reachable (field list is the primary navigation; viewer highlights follow), viewer operable without pointer (zoom/page controls buttons), confidence chips text+icon.
