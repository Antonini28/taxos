# 03 — Component Architecture (C4 Level 3)

## 1. taxos-api — module structure

The core service is a **modular monolith** with boundaries enforced by tooling (import-linter contracts in CI): modules may depend on `shared` and on other modules **only via their published service interfaces or domain events** — never on internals, never via cross-module table joins.

```mermaid
flowchart TB
    subgraph API["taxos-api"]
        subgraph Modules["Domain modules"]
            IDN["identity
            users, roles, permissions,
            OIDC integration, sessions"]
            MD["masterdata
            tenants, entities, jurisdictions,
            registrations, calendars"]
            ING["ingestion
            batches, schema registry,
            validation rules, quarantine"]
            CMP["compliance
            VAT engine host, rule-pack loader,
            computations, lineage"]
            WF["workflow
            work items, state machine,
            approvals, SoD checks"]
            RSK["risk
            anomaly registry, dispositions,
            score explanations"]
            RPT["reporting
            aggregates, dashboards API,
            evidence packs"]
            AUD["audit
            append-only log, hash chain,
            attestation export"]
        end
        subgraph Shared["shared kernel"]
            AUTHZ["authz — RBAC/ABAC policy engine"]
            OUTBOX["events — outbox publisher"]
            REPO["persistence — UoW, repositories, RLS session"]
            OBS["telemetry — OTel, structured logging"]
            TOOLGW["tool_gateway — agent-facing API surface"]
        end
    end
    Modules --> Shared
    WF -->|"ApprovalGranted"| OUTBOX
    ING -->|"BatchValidated"| OUTBOX
    CMP -->|"ComputationCompleted"| OUTBOX
    RSK -->|"AnomalyDetected"| OUTBOX
```

### Module contracts (what each publishes)

| Module | Service interface (sync) | Domain events (async) | Key invariants owned |
|---|---|---|---|
| identity | `AuthService`, `UserService` | `UserProvisioned`, `RoleChanged` | Every principal maps to roles + entity scopes; sessions carry tenant claim |
| masterdata | `EntityService`, `CalendarService` | `ObligationDue` (via scheduler scan) | Obligations derive from registrations + jurisdiction pack calendars |
| ingestion | `BatchService`, `ValidationService` | `BatchReceived`, `BatchValidated`, `RowsQuarantined` | No unvalidated row reaches computation; content-hash dedupe; batch immutable after validation |
| compliance | `ComputationService`, `RulePackService` | `ComputationCompleted` | Reproducibility (FR-205): computation = f(batch_ids, pack_version) recorded as snapshot; packs immutable once published |
| workflow | `WorkItemService`, `ApprovalService` | `WorkItemTransitioned`, `ApprovalGranted`, `EscalationRaised` | Legal state machine transitions only; SoD (preparer ≠ approver); approval binds to content hash |
| risk | `AnomalyService` | `AnomalyDetected`, `AnomalyDispositioned` | Every ML score stores model version + explanation payload; dispositions become labels |
| reporting | `DashboardService`, `EvidenceService` | `EvidencePackGenerated` | Aggregates rebuildable from source; packs assembled only from approved artifacts |
| audit | `AuditService` (write-only + query) | — | Append-only; hash chain continuity; called inside the same DB transaction as the mutation it records |

### The dependency rule

```
identity ← (all)          # everyone may check auth
masterdata ← ingestion, compliance, workflow, risk, reporting
ingestion ← compliance (read validated batches via interface)
compliance ← workflow (computation refs), reporting
risk ← reporting
audit ← (all, write-only)
NOTHING depends on reporting; reporting depends on read models only
```

Violations fail CI (`import-linter` contract file lives next to the code).

## 2. compliance module — the deterministic core (AP-2)

```mermaid
flowchart LR
    RPS["RulePackStore
    (Blob + DB metadata)
    packs: uk-vat@1.4.0 …"] --> LOADER["PackLoader
    signature check,
    schema validation"]
    LOADER --> ENG["ComputationEngine
    pure function:
    (transactions, pack, params)
    → ComputationResult"]
    VB["Validated batches"] --> ENG
    ENG --> SNAP["ComputationSnapshot
    inputs hash, pack version,
    box values, per-line lineage"]
    SNAP --> DB[("computations +
    computation_lines")]
```

Engine properties, mechanically enforced:
- **Pure and side-effect free** — the engine is a library function; property-based tests (Hypothesis) assert determinism (same inputs ⇒ identical output hash).
- **Decimal arithmetic only** (`decimal.Decimal`, HMRC rounding rules encoded per pack) — floats are banned by lint rule in the compliance module.
- **Rule packs are data** (YAML/JSON: rate tables, box mappings, code classifications, effective dates + citation references to HMRC manual paragraphs), signed and immutable once published. Adding a jurisdiction = authoring a pack + calendar (AP-3). Pack schema is versioned independently of pack content.
- **No I/O inside the engine** — inputs are materialised before invocation, which is what makes snapshots complete and replay trivial.

## 3. taxos-agents — component view

Framework-agnostic seams now; framework selection is Phase 3 (ADR-013 reserved).

```mermaid
flowchart TB
    subgraph AGT["taxos-agents"]
        SUP["Supervisor
        plan → route → track"]
        REG["AgentRegistry
        config-declared agents,
        capabilities, tool grants"]
        subgraph Specialists["Specialist agents (MVP set)"]
            DA["DataAgent"]
            VA["VATAgent"]
            FA["FraudAgent"]
            RA["ReportingAgent"]
        end
        CRT["Critic (R2)"]
        MEM["MemoryStore
        run state (Postgres),
        episodic summaries"]
        TC["ToolClient
        typed clients for Tool Gateway,
        per-agent allow-list,
        scoped service tokens"]
        TRC["RunTracer
        every step → agent_runs/agent_steps
        + OTel spans"]
    end
    SUP --> Specialists
    Specialists --> TC
    Specialists --> MEM
    SUP & Specialists --> TRC
    TC -->|"HTTPS"| GWAPI["taxos-api /tool-gateway/*"]
```

Two boundaries do the governance work:
1. **ToolClient allow-list** — an agent's tool grants are declared in the registry config; the ToolClient refuses undeclared calls *and* the Tool Gateway independently verifies the grant server-side (defence in depth). The VATAgent can call `get_validated_batch`, `run_vat_computation`, `create_work_item` — it has no tool that files, emails, or approves. Approval endpoints are not exposed on the Tool Gateway at all.
2. **RunTracer** — steps are recorded before/after every LLM and tool call (FR-302); a run that cannot trace cannot proceed (tracing is not best-effort).

## 4. taxos-workers — pipeline components

| Queue | Components | Trigger |
|---|---|---|
| `pipelines` | `BatchValidator` (schema registry → rule checks → quarantine writer), `LineageIndexer` | `BatchReceived` event / upload task |
| `ml` | `AnomalyScanner` (rules + IsolationForest at MVP), `ScoreExplainer` (SHAP, R2), `DriftMonitor` (R2) | `BatchValidated`, schedule |
| `exports` | `EvidencePackBuilder` (collect approved computation + lineage + approvals + agent traces → PDF/ZIP → Blob), `ReportRenderer` (R3) | user request task |
| `notifications` | `DeadlineScanner` (RAG transitions per US-302), `Notifier` (email/in-app) | Celery Beat schedule, workflow events |
| `outbox` | `OutboxRelay` (poll outbox table → publish to bus, exactly-once via row locking) | continuous |

Workers import the same domain layer as taxos-api — one implementation of validation, lineage, and audit writes (communication rule #2, doc 02).
