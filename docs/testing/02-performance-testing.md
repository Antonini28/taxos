# 02 — Performance Testing

## 1. Targets under test (from NFR-05/06/09 + SLOs in Phase 2 doc 09)

| ID | Target | Suite |
|---|---|---|
| P-1 | Interactive API p95 < 300ms @ nominal load | `api-baseline` |
| P-2 | Dashboard p95 < 500ms (aggregate reads) | `dashboard` |
| P-3 | Batch validation ≥ 1M rows/hour sustained | `pipeline-throughput` |
| P-4 | Event delivery (outbox→consumer) p95 < 5s under load | `eventing` |
| P-5 | WS fan-out: 500 concurrent connections, update p95 < 2s | `realtime` |
| P-6 | `search_knowledge` p95 < 700ms @ 10 concurrent | `retrieval` |
| P-7 | Graceful behaviour at 2× nominal (degrade, don't fall) | `stress` |
| P-8 | No leak/degradation over 8h at nominal | `soak` |
| P-9 | Audit-chain write serialisation holds at peak mutation rate (ADR-009 risk made measurable) | `chain-contention` |

## 2. Workload model (the honest shape, not synthetic uniformity)

Modelled on the personas' day: morning read-burst (dashboards, queues — 70% reads), period-end write-burst (uploads + validations + computations), continuous background (agents, scans, projections). Load mix per virtual-user class: Analyst (list/detail/upload), Reviewer (queue/evidence/approve), Executive (dashboard/drill), Agent-runtime (tool-gateway calls — replayed from recorded traces at realistic think-times), Pipeline (event-driven, triggered by seeded uploads). Peak model: quarter-end day = 3× nominal reads, 10× uploads, all tenants of the `multi` profile concurrently — **the number that matters for the managed-service story (P6)**.

## 3. Suites (k6; scenarios-as-code in `tests/perf/`)

| Suite | Shape | Key assertions |
|---|---|---|
| `api-baseline` | 30-min steady nominal | P-1 per endpoint class; error rate <0.1%; no p99 cliff |
| `dashboard` | Read-burst ramp | P-2; cache-hit ratio sanity (invalidation storm ≠ stampede — singleflight verified) |
| `pipeline-throughput` | Seeded 1M-row uploads, measure end-to-end | P-3; quarantine ratio unchanged at volume (correctness under load); KEDA scale-out/in curves recorded |
| `eventing` | Mutation storm | P-4; outbox lag; no consumer-group starvation |
| `realtime` | 500 WS + event storm | P-5; memory per connection; reconnect stampede behaviour |
| `retrieval` | Concurrent mixed queries | P-6; rerank degradation path fires correctly under provider slowness |
| `stress` | Step to 2×, hold, step down | P-7: rate-limit shedding (429s, not 5xxs), queues absorb, recovery time to SLO |
| `soak` | 8h nominal + background churn | P-8: RSS flat, connection pools stable, chain tip lag flat, no partition bloat surprises |
| `chain-contention` | Max concurrent audited mutations per tenant + across tenants | P-9: per-tenant chain serialisation cost measured; documented headroom vs realistic peak |

## 4. Method rules

- Perf env per doc 01 §3 (prod-shaped ephemeral); `scale` seed; **stub LLM** for everything except `retrieval` (model latencies are the provider's number, not ours — we measure our machinery; agent-run *orchestration* overhead is measured with stub latencies injected at realistic distributions).
- Every run: warm-up excluded, 3 repetitions, medians-of-p95 reported with variance; OTel traces sampled at 100% during runs — every regression comes with its flame-path, not just a number.
- Regression policy: nightly `api-baseline` smoke on staging (small SKU, *trend* gate ±15% vs 7-day median — absolute numbers on staging are weather); evidence runs per release train on the perf env produce the **published performance report** (`docs/evidence/perf-<train>.md`: environment BOM, methodology, results tables, flame-path notes) — the artifact NFR-06 demands and the portfolio shows.
- Capacity statement per train derived from evidence: "at prod reference SKUs: N analysts + M concurrent batch-quarters + K agent runs within SLO; first bottleneck: X at ~Y load; next mitigation: Z (pre-designed in doc 04 §7 scale path)" — capacity planning as a maintained fact, not tribal knowledge.

## 5. Profiling & optimisation discipline

Optimisation only against evidence (measured hot path + SLO breach or headroom target), in this order: query plans (pg_stat_statements + `EXPLAIN` on top offenders; partition pruning verified), N+1 elimination (SQLAlchemy eager-load audits on flagged traces), cache placement per ADR-011 (never new cache tiers ad hoc), then code. Every optimisation PR carries before/after run output from the relevant suite — "should be faster" doesn't merge.
