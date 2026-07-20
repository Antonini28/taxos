# 04 — Async & Tasks (taxos-workers)

## 1. Celery configuration (normative)

```python
app = Celery("taxos")
app.conf.update(
    broker_url=settings.redis.broker_dsn, result_backend=None,   # results in domain tables, not Celery
    task_acks_late=True, task_reject_on_worker_lost=True,        # at-least-once, always
    task_queues=[Queue(q) for q in ("pipelines", "ml", "exports", "notifications", "outbox")],
    task_routes=ROUTES,                                          # explicit per-task queue map
    worker_prefetch_multiplier=1,                                # fair dispatch for long tasks
    task_time_limit=3600, task_soft_time_limit=3300,
    broker_transport_options={"visibility_timeout": 4000},       # > time_limit: no double-run window
    beat_schedule=BEAT,                                          # doc 05 §4 (Phase 2) transcribed
)
```

`acks_late + reject_on_worker_lost` makes redelivery-after-crash the assumed behaviour — which is why the idempotent base task exists.

## 2. Idempotent task base (every task inherits)

```python
class TaxosTask(Task):
    """At-least-once + idempotency-key dedupe + OTel + structured failure."""
    autoretry_for = (TransientError,); retry_backoff = True; retry_jitter = True; max_retries = 3

    def __call__(self, *args, **kwargs):
        key = kwargs.pop("idempotency_key")             # REQUIRED — enqueue helper enforces
        with task_span(self.name, key):                 # trace context from kwargs carrier
            with idempotency_guard(key, ttl=86400) as fresh:   # Redis SETNX + Postgres watermark
                if not fresh:
                    log.info("duplicate suppressed", key=key); return
                return super().__call__(*args, **kwargs)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        record_task_failure(self.name, kwargs, exc)     # metric + DLQ table row + alert routing
```

Task rules: tasks receive **ids, never payloads** (re-read state inside the task — stale-payload bugs die here); tasks are thin orchestration over `taxos_core` services (same UoW path — communication rule #2, Phase 2 doc 02); permanent failures land in a `task_dlq` table with full context, replayable by runbook command (`tools/dlq replay`), never auto-replayed.

## 3. Outbox relay (the one loop that must not lie)

```python
@app.task(base=TaxosTask, queue="outbox")
def relay_outbox(batch: int = 200):
    while True:
        with platform_session() as s:                       # platform role: outbox is cross-tenant infra
            rows = s.execute(
                select(OutboxEvent).where(OutboxEvent.published_at.is_(None))
                .order_by(OutboxEvent.seq).limit(batch)
                .with_for_update(skip_locked=True)).scalars().all()
            if not rows: return
            for row in rows:
                publisher.publish(row.to_bus_event())       # broker adapter (ADR-003)
                row.published_at = now()                    # only after broker ack
            s.commit()
```

Crash between publish and mark ⇒ republish (at-least-once — consumers dedupe by `event_id`); relay lag metric (`outbox_oldest_unpublished_seconds`) is an SLO (doc 09); the relay runs as a dedicated always-on worker (beat kicks a watchdog task that alerts if the relay stalls).

## 4. Event consumers

One consumer group per concern (cache invalidator, reporting projector, notification fan-out, agent-run starter, WS bridge). Consumer template: dedupe on `event_id` watermark table → handle inside UoW where mutations occur → poison messages to DLQ after 5 attempts with alert. Handlers restate their idempotency assumption in a docstring — reviewed like any contract.

## 5. WebSocket bridge

A slim consumer that maps bus events → `ws:{tenant}:{topic}` Redis pub/sub with scope metadata; the API's WS handler does final per-connection filtering (Phase 2 doc 05 §5). The bridge holds no state — restart-safe by construction.

## 6. Scheduling

Beat runs in the scheduler container (single replica + Redis lock — Phase 2 doc 05 §4); every scheduled task is also manually invokable via an admin endpoint (FR-704) because "re-run the deadline scan now" is an operational reality; schedule definitions live in code with the task, not in ops config (drift-proof, reviewable).
