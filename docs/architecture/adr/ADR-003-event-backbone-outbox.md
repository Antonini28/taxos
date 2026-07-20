# ADR-003 — Transactional outbox + broker-abstracted event bus; Celery for tasks

**Status:** Accepted · 2026-07-20 · Principles: AP-4, AP-5

## Context
Async needs split into *commands* (run this pipeline — retried, routed, exactly-one-worker) and *facts* (domain events — fan-out, replayable, decoupled). Publishing events reliably alongside DB commits is the classic dual-write problem. Broker candidates: Kafka, RabbitMQ, Azure Service Bus, Redis Streams.

## Decision
1. **Tasks:** Celery over Redis broker (mature retries/routing/beat, KEDA-scalable, team-known).
2. **Events:** **transactional outbox** table written in the same DB transaction as state + audit; an OutboxRelay publishes to the bus. Consumers are idempotent (at-least-once).
3. **Broker abstraction:** an `EventPublisher`/`EventConsumer` port with two adapters — **Redis Streams** (local/dev/CI: zero extra infra) and **Azure Service Bus topics** (prod: managed, DLQ, sessions, zone redundancy).

## Alternatives considered
1. **Kafka** — gold standard for event streaming, but: cluster ops (or Confluent cost), partitions/consumer-group complexity, and throughput two orders beyond requirements. Classic over-engineering for <10k events/min. Revisit trigger: event replay analytics or >100k events/min.
2. **RabbitMQ** — solid, but self-managed on Azure vs Service Bus being native, and it adds nothing Service Bus lacks at our scale.
3. **Direct publish (no outbox)** — silent event loss on crash between commit and publish; unacceptable when events drive agent work and cache correctness.
4. **CDC/Debezium** — heavyweight ops (Kafka Connect) for what a 100ms poll with `SKIP LOCKED` achieves at this volume.
5. **One channel for everything (bus-only or Celery-only)** — conflates command and fact semantics; documented failure mode (doc 05 §1).

## Consequences
- (+) No lost or phantom events; state/audit/event atomicity underwrites the evidence guarantees.
- (+) Dev environment needs only Postgres + Redis; prod gets managed durability.
- (−) Outbox adds relay latency (~100–300ms) — fine for our SLO (event lag p95 < 5s).
- (−) Two async subsystems to monitor → unified queue/outbox dashboard (doc 09) is mandatory, not optional.
