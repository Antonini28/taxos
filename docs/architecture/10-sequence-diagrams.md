# 10 — Sequence Diagrams & Agent Communication Flow

## 1. Batch ingestion & validation (US-201)

```mermaid
sequenceDiagram
    actor U as Preparer (P2)
    participant FE as Frontend
    participant API as taxos-api (ingestion)
    participant BL as Blob
    participant DB as Postgres
    participant W as Worker (pipelines)
    participant WS as WebSocket

    U->>FE: upload extract (CSV, entity, period)
    FE->>API: POST /batches (multipart, Idempotency-Key)
    API->>API: authZ (PREPARER, entity scope), size caps
    API->>BL: store raw file (WORM)
    API->>DB: batch(RECEIVED) + content-hash dedupe check + audit + outbox(BatchReceived)
    API-->>FE: 202 {batch_id}
    Note over W: consumes BatchReceived
    W->>BL: stream file
    W->>DB: schema check → typed rows / quarantine rows (rule reasons)
    W->>DB: control totals, validation_result, batch(VALIDATED*) + audit + outbox(BatchValidated, RowsQuarantined)
    WS-->>FE: batch status + quarantine badge (live)
    U->>FE: open validation report / quarantine queue
```

## 2. Agent-orchestrated VAT cycle with approval gate (US-401/402) — the flagship flow

```mermaid
sequenceDiagram
    actor U as Preparer (P2)
    participant API as taxos-api
    participant BUS as Event Bus
    participant SUP as Supervisor (taxos-agents)
    participant VA as VATAgent
    participant FA as FraudAgent
    participant TG as Tool Gateway (taxos-api)
    participant ENG as Deterministic VAT Engine
    actor R as Reviewer (P3)

    U->>API: POST /agent-runs {"prepare Q2 VAT for UK-01"}
    API->>BUS: AgentRunRequested (after run row + audit)
    BUS->>SUP: consume
    SUP->>SUP: build bounded plan (steps, agents, budgets)
    SUP-->>API: plan persisted (agent_run) → WS streams to user

    SUP->>VA: step: prepare draft return
    VA->>TG: get_validated_batches(entity, period)
    TG->>TG: verify agent grant + run budget + scope
    VA->>TG: run_vat_computation(obligation, batch_ids)
    Note over TG,ENG: LLM never computes — the tool invokes<br/>the deterministic engine (AP-2)
    TG->>ENG: compute(rows, pack uk-vat@1.4.0)
    ENG-->>TG: snapshot: boxes + lineage + inputs_hash
    VA->>VA: LLM drafts narrative: variances vs prior period,<br/>exceptions summary (reasoning, not arithmetic)

    SUP->>FA: step: anomaly review
    FA->>TG: get_anomalies(period) / trigger_scan
    FA-->>SUP: flagged items + severity summary

    SUP->>TG: create_work_item(state=AWAITING_HUMAN_REVIEW,<br/>computation_id, narratives, anomaly refs)
    Note over SUP: run ends here — no agent tool<br/>can approve or file (by construction)

    R->>API: review: lineage drill-down, anomaly queue
    R->>API: POST /work-items/{id}/approvals (If-Match, content_hash)
    API->>API: SoD check (R ≠ preparer), RBAC, state check
    API->>API: approval + audit + outbox(ApprovalGranted)
    API-->>R: APPROVED — evidence pack now eligible
```

## 3. Escalation path (US-401 missing-data scenario, FR-306)

```mermaid
sequenceDiagram
    participant SUP as Supervisor
    participant DA as DataAgent
    participant TG as Tool Gateway
    participant BUS as Event Bus
    actor U as Preparer queue

    SUP->>DA: step: confirm inputs for plan
    DA->>TG: get_validated_batches(entity, period, source=payroll)
    TG-->>DA: [] (none)
    DA-->>SUP: gap report: payroll extract missing
    SUP->>TG: raise_escalation(run, reason, needed_input)
    TG->>BUS: EscalationRaised (run → WAITING_INPUT)
    BUS-->>U: notification + workspace card
    Note over SUP: no fabrication, no estimation —<br/>run parks until input arrives, then resumes plan
```

## 4. Authentication (OIDC + PKCE)

```mermaid
sequenceDiagram
    actor U as User
    participant FE as Next.js
    participant IDP as Entra ID
    participant API as taxos-api

    U->>FE: open app
    FE->>IDP: redirect authorize (PKCE challenge)
    IDP->>U: login + MFA (conditional access)
    IDP-->>FE: code
    FE->>API: exchange code (BFF pattern — tokens never in browser JS)
    API->>IDP: code + verifier → tokens
    API-->>FE: httpOnly session cookie (access 15m / rotating refresh)
    U->>FE: work
    FE->>API: requests with cookie
    API->>API: validate JWT, load AuthzContext (Redis-cached), policy per request
```

## 5. Evidence pack export (US-603/US-202)

```mermaid
sequenceDiagram
    actor A as Auditor/Risk Lead (P3)
    participant API as taxos-api
    participant W as Worker (exports)
    participant DB as Postgres
    participant BL as Blob (WORM)

    A->>API: POST /work-items/{id}/evidence-pack
    API->>API: authZ (AUDITOR/REVIEWER), state must be APPROVED
    API-->>A: 202 {job}
    W->>DB: collect: computation snapshot, lineage set, approvals,<br/>agent trace, validation reports, audit slice
    W->>W: verify audit-chain continuity for the slice
    W->>BL: render PDF + ZIP → evidence/ (immutable)
    W-->>A: notification + signed URL (time-boxed)
```

## 6. Agent communication model (structural view)

```mermaid
flowchart TB
    subgraph Governance["Governed boundary (taxos-api)"]
        TG["Tool Gateway
        allow-list · budgets · scope"]
        WFG["Workflow gate
        human approvals only"]
    end
    SUP["Supervisor
    (plans, routes, tracks,
    enforces step budgets)"]
    DA["DataAgent"] ; VA["VATAgent"] ; FA["FraudAgent"] ; RA["ReportingAgent"]
    CRT["Critic (R2)
    rubric review before
    human handoff"]
    MEM[("Shared run state
    + memory (Postgres)")]

    SUP -->|"typed task envelopes
    (goal, context refs, budget)"| DA & VA & FA & RA
    DA & VA & FA & RA -->|"typed results
    (output, confidence, citations)"| SUP
    SUP --> CRT
    CRT -->|"pass / revise(feedback)
    max 2 loops"| SUP
    DA & VA & FA & RA --> TG
    SUP --> MEM
    DA & VA & FA & RA --> MEM
    TG -.->|"no path exists"| WFG
```

Communication rules: agents never message each other directly — all coordination flows through the Supervisor via **typed envelopes** (goal, input refs, budget, deadline) and typed results (output, confidence, citations, cost). This makes every hop traceable (FR-302), budget-enforceable, and framework-portable (the envelope contract survives a Phase 3 framework swap — ADR-012). Peer-to-peer agent chatter was rejected: it's untraceable, unbudgetable, and adds no capability a supervisor route lacks.
