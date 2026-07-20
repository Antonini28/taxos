# 06 — User Stories, Acceptance Criteria & Product Backlog

Stories follow the standard format with Gherkin acceptance criteria (they become executable test skeletons in Phase 10). Story points use Fibonacci; priority = release train from doc 05. This is the seed backlog — grooming happens per release train.

## Epic E2 — Data ingestion & validation

### US-201 (P2, FR-101/102) — Upload and validate a transaction batch — **R1, 8 pts**
*As a* Tax Operations Manager, *I want* to upload ERP extracts and receive an immediate validation report, *so that* bad data is caught before it contaminates any computation.

```gherkin
Scenario: Valid batch is accepted
  Given a CSV of AP invoices matching the published schema for entity "UK-01"
  When I upload it to period 2026-Q2
  Then the batch status becomes "VALIDATED" within 2 minutes for 100k rows
  And a validation report shows row counts, control totals, and zero errors

Scenario: Invalid rows are quarantined, not silently dropped
  Given a batch where 12 rows have unknown VAT codes
  When validation completes
  Then exactly those 12 rows are in the quarantine queue with rule-level reasons
  And the batch status is "VALIDATED_WITH_EXCEPTIONS"
  And no quarantined row is included in any downstream computation

Scenario: Duplicate batch upload is rejected
  Given the same file (by content hash) was already ingested for the period
  When I upload it again
  Then the upload is rejected with reference to the original batch
```

### US-202 (P3, FR-103) — Trace any figure to source — **R1, 5 pts**
*As a* Tax Risk Lead, *I want* to click any computed figure and see the source transactions and transformation steps, *so that* I can answer authority enquiries with evidence.

```gherkin
Scenario: Lineage drill-down from a VAT return box
  Given an approved VAT return for entity "UK-01" period 2026-Q2
  When I open lineage for Box 4
  Then I see the contributing transaction set, applied rule versions, and batch IDs
  And the sum of contributing amounts equals the box value exactly
```

## Epic E3 — VAT engine

### US-301 (P2, FR-201/205) — Deterministic draft VAT return — **R1, 13 pts**
*As a* Tax Operations Manager, *I want* the platform to compute a draft UK 9-box VAT return from validated data, *so that* preparation becomes review.

```gherkin
Scenario: Reproducibility
  Given validated data for entity "UK-01" period 2026-Q2 and VAT rules version 1.4.0
  When the computation runs twice
  Then both runs produce byte-identical box values and computation snapshots

Scenario: Reverse charge handling
  Given a purchase invoice flagged as domestic reverse charge (construction services)
  When the return is computed
  Then output VAT appears in Box 1 and recoverable input VAT in Box 4 per the rule's cited HMRC reference

Scenario: Rule version change does not mutate history
  Given rules version 1.5.0 is published after the return was computed
  Then the stored return still references 1.4.0 and recomputation under 1.5.0 requires an explicit, logged action
```

### US-302 (P1, FR-204) — Compliance calendar with RAG status — **R1, 5 pts**
```gherkin
Scenario: Deadline risk surfacing
  Given entity "UK-01" has a VAT return due in 7 days with status "DRAFT"
  When the Head of Tax opens the dashboard
  Then the obligation shows AMBER; it becomes RED at 3 days if not "APPROVED"
  And a notification is sent to the assigned owner at each transition
```

## Epic E4 — Core agent team

### US-401 (P2, FR-301/304) — Supervisor runs the VAT cycle — **R1, 13 pts**
*As a* Tax Operations Manager, *I want* to instruct the agent team to "prepare Q2 VAT for UK-01" and watch it execute, *so that* multi-step work happens without my micro-management.

```gherkin
Scenario: Happy-path orchestration
  Given validated data exists for the entity-period
  When I submit the instruction in the agent workspace
  Then the Supervisor produces a visible plan (steps, assigned agents)
  And Data → VAT → Fraud → Reporting agents execute with live status updates
  And the run ends in "AWAITING_HUMAN_REVIEW" — never "FILED"

Scenario: Missing data escalation (FR-306)
  Given no payroll extract exists for the period
  When the plan requires it
  Then the run pauses with an escalation to the preparer queue naming the exact gap
  And no agent fabricates or estimates the missing values
```

### US-402 (P1, FR-303) — Approval gate — **R1, 8 pts**
```gherkin
Scenario: State change requires named approver
  Given a draft return in "AWAITING_HUMAN_REVIEW"
  When reviewer "priya@corp.com" approves with comment
  Then status becomes "APPROVED" recording approver, timestamp, and content hash of what was approved
  And any later change to inputs reverts status to "DRAFT" and voids the approval

Scenario: Self-approval is blocked
  Given the preparer and reviewer are the same user
  Then approval is rejected with a segregation-of-duties error
```

### US-403 (P3, FR-302) — Full agent action log — **R1, 5 pts**
```gherkin
Scenario: Reconstruct an agent run
  Given any completed run
  When I open its trace
  Then every step shows agent, model, prompt/tool inputs, outputs, tokens, cost, and duration
  And the trace is immutable (append-only, verified by hash chain)
```

## Epic E5/E6 — Governance & core UI

### US-501 (P5, FR-701) — RBAC with segregation of duties — **R1, 8 pts**
```gherkin
Scenario: Preparer cannot approve
  Given a user with only the "PREPARER" role
  When they call the approval endpoint directly (API, not UI)
  Then the response is 403 and the attempt is audit-logged
```

### US-601 (P1/P4, FR-601) — Executive dashboard — **R1, 8 pts**
```gherkin
Scenario: Five-minute CFO view
  Given the demo dataset is loaded
  When the CFO opens the Executive Dashboard
  Then compliance heat map, upcoming deadlines, open anomaly value, and cash-tax KPIs render in < 500 ms p95
  And every KPI supports drill-down to its underlying records
```

## Epic E8 — Risk ML (R2 highlights)

### US-801 (P3, FR-501/506) — Anomaly queue with disposition — **R1(rules+IF)/R2(ML), 13 pts**
```gherkin
Scenario: Seeded duplicate detection
  Given the demo dataset contains 14 seeded near-duplicate invoices (same supplier, ±2% amount, ±5 days)
  When the fraud scan runs
  Then at least 13 are flagged with type "POSSIBLE_DUPLICATE" and a match-pair link
  And dispositioning one as "CONFIRMED" stores the label for future training

Scenario: Explainability (FR-502)
  Given any ML-scored anomaly
  When I open its detail view
  Then the top SHAP feature contributions are displayed in plain language
```

## Epic E7 — Knowledge platform (R2 highlights)

### US-701 (P2, FR-402/403) — Cited answers only — **R2, 13 pts**
```gherkin
Scenario: Grounded answer
  When I ask "Can we recover input VAT on staff entertainment?"
  Then the answer cites specific corpus passages (source, section, link) for each claim

Scenario: Refusal on missing knowledge
  When I ask about a jurisdiction not in the corpus
  Then the system states it lacks sources and offers escalation — it does not improvise
```

## Backlog register (groomed seed — top 30)

| Rank | ID | Story | Epic | Release | Pts | Reqs |
|---|---|---|---|---|---|---|
| 1 | US-101 | Platform skeleton: monorepo, CI, auth, docker compose, deploy | E1 | R1 | 13 | NFR-10/12 |
| 2 | US-104 | Master data: entities, jurisdictions, calendars | E2 | R1 | 5 | FR-104 |
| 3 | US-201 | Batch upload + validation | E2 | R1 | 8 | FR-101/102 |
| 4 | US-202 | Lineage drill-down | E2 | R1 | 5 | FR-103 |
| 5 | US-301 | Deterministic VAT return | E3 | R1 | 13 | FR-201/205 |
| 6 | US-302 | Compliance calendar | E3 | R1 | 5 | FR-204 |
| 7 | US-401 | Supervisor VAT cycle | E4 | R1 | 13 | FR-301/304 |
| 8 | US-402 | Approval gates + SoD | E4 | R1 | 8 | FR-303 |
| 9 | US-403 | Agent trace log | E4 | R1 | 5 | FR-302 |
| 10 | US-501 | RBAC | E5 | R1 | 8 | FR-701 |
| 11 | US-502 | Immutable audit log | E5 | R1 | 5 | FR-702 |
| 12 | US-601 | Executive dashboard | E6 | R1 | 8 | FR-601 |
| 13 | US-602 | VAT analytics + drill-down | E6 | R1 | 8 | FR-602 |
| 14 | US-801 | Anomaly queue (rules + Isolation Forest) | E8 | R1 | 13 | FR-501/506 |
| 15 | US-603 | Evidence pack export | E6 | R1 | 5 | FR-604 |
| 16 | US-701 | RAG corpus + cited answers | E7 | R2 | 13 | FR-401/402/403 |
| 17 | US-702 | Eval harness in CI | E7 | R2 | 8 | NFR-07 |
| 18 | US-802 | Supervised risk scoring + SHAP | E8 | R2 | 13 | FR-502 |
| 19 | US-901 | Agent chat workspace (full) | E9 | R2 | 13 | FR-304 |
| 20 | US-1001 | CT computation + adjustment schedule | E10 | R2 | 13 | FR-202 |
| 21 | US-404 | Critic/reflection loop | E4 | R2 | 8 | FR-305 |
| 22 | US-1101 | Liability forecasting | E11 | R2 | 8 | FR-504 |
| 23 | US-803 | Model registry + drift monitoring | E8 | R2 | 8 | FR-505 |
| 24 | US-1201 | Tenant isolation + ABAC | E12 | R3 | 13 | FR-703, NFR-03 |
| 25 | US-1301 | Regulatory monitoring → impact queue | E13 | R3 | 13 | FR-404 |
| 26 | US-1401 | Board pack generation + approval | E14 | R3 | 8 | FR-603 |
| 27 | US-1501 | Security test suite + prompt-injection defences | E15 | R3 | 8 | NFR-02 |
| 28 | US-1601 | Observability dashboards + SLOs | E16 | R3 | 8 | NFR-05/11 |
| 29 | US-1701 | Load test evidence | E17 | R4 | 5 | NFR-06 |
| 30 | US-2001 | Public API + webhooks | E20 | R4 | 8 | FR-706 |

**Definition of Done (applies to every story):** code merged via PR with review checklist; unit + integration tests green in CI; docs updated; audit-log coverage verified for any new state change; no new critical/high findings from dependency & secret scanning; demoable from the deployed environment.
