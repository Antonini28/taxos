# 05 — Operations: Cost, Runbooks, DR

## 1. SKU & cost model (monthly, GBP, indicative July-2026 rates)

### Portfolio/demo posture (staging profile, scale-to-zero aggressive)

| Service | SKU | Est./mo |
|---|---|---|
| Container Apps (5 apps) | Consumption; agents/workers scale-to-zero; api/frontend min 0–1 | £5–20 (traffic-driven) |
| PostgreSQL Flexible | B2s burstable, 64GB, no HA | £30–40 |
| Redis | Basic C0 | £13 |
| Service Bus | Standard | £8 |
| Storage | LRS hot, <50GB | £2–5 |
| Key Vault / App Config | Standard / Free tier | £2 |
| Log Analytics + App Insights | PAYG, 30d retention, sampling | £5–15 |
| ACR | Basic | £4 |
| Azure OpenAI | PAYG; stub mode default, evals budgeted | £5–30 (usage) |
| **Total** | | **~£75–140/mo**, teardown script → ~£0 idle |

### Production posture (enterprise reference — the "what would this cost for real" answer)

| Service | SKU | Est./mo |
|---|---|---|
| Container Apps | Dedicated D4 profile, api min 2 | £250–400 |
| PostgreSQL | D4ds_v5, zone-redundant HA, 512GB, geo-backup | £600–800 |
| Redis | Standard C1 | £80 |
| Service Bus | Premium (1 MU, zones) | £550 |
| Storage | RA-GRS + WORM | £50–150 |
| Front Door + WAF | Standard | £250+ |
| Observability | ~10GB/day | £300–500 |
| Azure OpenAI | PTU or PAYG at volume | £500–5,000 (workload) |
| AI Search (enterprise swap) | Standard S1 | £200 |
| **Total** | | **~£2.8k–8k/mo** before OpenAI volume — honest, and the per-tenant marginal cost story (ADR-006) is what makes the platform economics work |

Cost controls: budget alerts (50/80/100%) on every RG · daily cost export → dashboard tile in `/admin/system` · per-run LLM cost caps (Phase 3) are the AI-spend circuit breaker · `just infra-down` / `just infra-up` scripted teardown/rebuild (≤30 min to demo-ready, seeded — the portfolio's idle-cost answer).

## 2. Runbook index (`docs/runbooks/` — each: meaning, blast radius, first checks, kill switches, escalation)

| Runbook | Trigger |
|---|---|
| `deploy-rollback` | Failed release, burn-rate alert post-deploy |
| `db-failover` / `db-restore-pitr` | Zone failure / data corruption (includes timed quarterly rehearsal record) |
| `dr-restore-region` | Region loss — pilot-light build-out in ukwest (target: RTO ≤ 4h, rehearsed) |
| `queue-backlog` | Queue age/depth alerts (KEDA ceiling, poison messages, DLQ triage + replay) |
| `outbox-stall` | Relay lag SLO breach |
| `llm-provider-outage` | Circuit-open alert (verify parked runs, comms, provider status, resume verification) |
| `audit-chain-failure` | Integrity job or Audit-Readiness agent critical alert — **security incident path**, preserve evidence, engage chain-verification procedure |
| `cross-tenant-suspicion` | Any RLS/tenancy alarm — incident path, tenant comms template |
| `cost-spike` | Budget alert (top offenders query, AI-spend breakdown, kill switches) |
| `cert-dns-issues` | Ingress/domain failures |
| `secret-rotation` | Scheduled + emergency rotation procedure |
| `pack-publish` / `pack-rollback` | Rule-pack release governance (sign, effective-date, entity pinning) |

Alert→runbook linkage is enforced by review: an alert PR without a runbook link doesn't merge (Phase 2 doc 09 §4).

## 3. Backup & DR procedures (making Phase 2 doc 08 §5 executable)

- **Postgres:** PITR 35d + geo-redundant backup; `db-restore-pitr` runbook includes the *verification* step everyone forgets (restore to side server → checksum row counts + audit-chain verify → then swap) — a restore that isn't verified is a second incident.
- **Blob:** RA-GRS; WORM containers replicate immutably; evidence-container legal-hold procedure documented.
- **Rebuildables** (Redis, Service Bus topology, dashboards, ACA): Terraform + pipelines; explicitly listed as *not backed up, by design* — the DR plan says so out loud so nobody invents backup jobs for rebuildable state.
- **DR rehearsal:** quarterly, scripted (`dr-restore` pipeline), timed, results logged in `docs/runbooks/rehearsals.md` — the artifact an ISO/SOC2 audit (Phase 9) actually asks for.
- **Backup of the *product's* evidence:** evidence packs + audit chain anchors already live in WORM storage (Phase 2) — DR for the trust layer is replication, not backup jobs.

## 4. Operational calendar

| Cadence | Activity |
|---|---|
| Daily (auto) | Drift plan check, cost export, audit-chain verify (staging+prod), DLQ scan |
| Weekly (auto) | Rollback drill (staging), dependency/CVE report, eval-suite trend report |
| Monthly | Secret-rotation batch, SKU right-sizing review, alert-noise review (fire rate vs action rate) |
| Quarterly | DR rehearsal (timed), access review (PIM + DB roles + KV policies), pack/citation drift audit |
