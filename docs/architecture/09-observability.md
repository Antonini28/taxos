# 09 — Observability

## 1. Strategy

One instrumentation standard (**OpenTelemetry**) across all services; backends are pluggable (App Insights/Log Analytics in Azure, optional local Grafana stack via compose profile). Observability here has an unusual fourth pillar: **agent telemetry** — for an agentic platform, "what did the AI do and what did it cost" is as operationally critical as latency.

## 2. The pillars

### Logs
- Structured JSON only (`structlog`); every record carries `trace_id`, `span_id`, `tenant_id`, `actor`, `request_id`.
- No PII in logs — the pseudonymisation boundary (doc 04 §6) applies to log payloads; log-scrubbing processor as backstop.
- Levels are contractual: `WARNING` = human should look eventually, `ERROR` = alert can fire — enforced in review (alert fatigue is an architecture failure).
- Audit events are **not** logs — they live in the audit table (doc 07 §6); logs are operational and disposable (30–90d retention), audit is evidence.

### Traces
- OTel auto-instrumentation (FastAPI, SQLAlchemy, Redis, Celery, httpx) + manual spans around domain operations.
- Context propagates across async hops: HTTP → outbox event (carrier headers in payload) → consumer → Celery task → WS push. One `trace_id` follows a batch from upload to evidence pack; RFC 9457 errors return it to the UI (doc 06 §3).
- Agent runs are traces: run = root span, each plan step/LLM call/tool call = child spans with token counts, model, cost attributes — the agent trace view (FR-302) is a projection of the same data.

### Metrics
| Class | Examples | Alert basis |
|---|---|---|
| RED per endpoint | rate, error %, p50/p95/p99 | Burn-rate alerts on SLOs |
| Queues | depth, age-of-oldest, DLQ count per queue | DLQ > 0 (page), oldest > threshold |
| Pipelines | rows/s validated, quarantine ratio, batch duration | Quarantine-ratio spike (data-quality regression) |
| Business/compliance | obligations by RAG status, approvals pending age, anomalies open by severity | RED obligations (notify P1 path) |
| **Agent** | runs by status, steps/run, tokens & £-cost per run/tenant/model, escalation rate, critic-rejection rate, provider-circuit state | Cost budget burn (NFR-08), escalation-rate spike |
| ML (R2) | score distributions, PSI/KS drift stats, disposition agreement rate | Drift threshold breach |

### Agent/AI quality (fourth pillar, R2+)
Eval harness results (RAG citation-support rate, engine reproducibility checks, critic rubric scores) are emitted as metrics from CI and staging runs — quality regressions trend on the same dashboards as latency (NFR-07 made observable).

## 3. SLOs (NFR-05/06 operationalised)

| SLO | Target | Window |
|---|---|---|
| API availability (5xx-based) | 99.9% | 30d rolling |
| Interactive API latency | p95 < 300ms | 7d |
| Dashboard latency | p95 < 500ms | 7d |
| Batch validation throughput | 1M rows/hr sustained | per-run |
| Agent run completion (non-escalated) | 95% without technical failure | 7d |
| Event delivery lag (outbox→consumer) | p95 < 5s | 7d |

Multi-window burn-rate alerting (fast burn pages, slow burn tickets); error budgets gate risky deploys (burned budget ⇒ feature freeze convention documented in the runbook).

## 4. Dashboards & runbooks

Dashboards-as-code (committed JSON): *Service health* (RED + SLO burn), *Async health* (queues, outbox lag, DLQ), *Agent operations* (runs, cost, escalations — doubles as the FR-307 admin UI data source), *Data quality* (ingestion/quarantine), *Compliance posture* (business metrics for P1/P3 views).
Every alert links to a runbook page (`docs/runbooks/`) with: meaning, blast radius, first checks, kill switches (doc 08 §6), escalation. An alert without a runbook doesn't ship.
