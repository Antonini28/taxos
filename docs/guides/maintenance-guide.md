# Maintenance Guide (Operator's Digest)

The operating manual in one page; depth lives in [runbooks](../runbooks/) and the [cloud docs](../cloud/README.md).

## Daily posture (10 minutes)

Quality/health dashboard (`/admin/system` or Grafana): all suites green on main? · queue depths + oldest-age nominal? · outbox lag < SLO? · audit-chain verify green (staging+prod)? · DLQ empty? · error-budget burn normal? · overnight cost within envelope? Anything amber has an alert → every alert links its runbook — follow it, don't improvise.

## The kill switches (know these cold)

| Switch | Effect | Use when |
|---|---|---|
| `ff_agent_runs_enabled=off` | New runs blocked; active runs park cleanly | Agent misbehaviour, provider incident, injection suspicion |
| Provider circuit (auto, can force-open) | Runs park in WAITING_PROVIDER | AOAI degradation |
| `ff_ingestion_enabled=off` | Uploads rejected with notice | Pipeline corruption suspicion |
| Rate-limit overrides (per tenant) | Throttle a noisy tenant | Fairness incidents |
| Revision traffic flip | Instant version rollback | Bad deploy (`just rollback <env>`) |

## Scheduled operations (automated; your job is noticing failures)

Daily: drift plan, chain verify, DLQ scan, cost export · Weekly: staging rollback drill, CVE report, eval trends · Monthly: secret-rotation batch, SKU review, alert-noise review · Quarterly: DR rehearsal (timed, logged), access review, pack/citation drift audit. Full calendar: [operations §4](../cloud/05-operations.md).

## Interventions you'll actually perform

| Situation | Action |
|---|---|
| DLQ items | `just dlq` → triage per [queue-backlog runbook]; replay only after cause fixed |
| Parked runs after provider recovery | Verify circuit closed → runs auto-resume; spot-check one trace |
| Retrain ticket (drift) | Follow [MLOps §4](../ml/06-mlops.md) — analyst review first; never blind-retrain |
| Pack release | [pack-publish runbook]: sign → effective-date → entity pinning review → publish; rollback = repin |
| New tenant | Admin → tenant + entities + calendars; detectors auto-start at rules rung; verify RLS canaries seeded |
| Tenant offboarding | Export evidence packs → retention clock → erasure per [privacy runbook] (mapping destruction, WORM windows respected) |
| Certificate/DNS | [cert-dns runbook] — the only ops task with a hard external deadline; alerts fire at T-30d |

## Escalation & incidents

Severity matrix + playbooks: [incident response](../security/06-incident-response.md). Non-negotiables: evidence preservation **before** remediation (snapshot first — the playbooks open with it); audit-chain anomalies are SEV-1 until proven benign; cross-tenant suspicion goes straight to the IR path, not debugging. Post-incident: blameless review ≤ 5 days, actions become issues, suites get a fixture — every incident leaves the system stronger, by policy.

## Capacity & cost

Monthly: SKU right-sizing vs the [capacity statement](../testing/02-performance-testing.md#4-method-rules) from the latest evidence run · watch the three growth pressures with pre-designed responses ([scale path](../architecture/04-data-architecture.md#7-scale-path-stated-now-exercised-later)): transaction volume → partition hygiene; corpus growth → AI Search swap; tenant count → per-tenant DB tier. Cost spike → [runbook] (top-offender query first; it's usually LLM spend or log ingestion — both have caps to check).
