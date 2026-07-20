# 03 — Persistence: the Audited Unit of Work

This document specifies the single most load-bearing code in the platform: the write path that makes "state + audit + outbox commit atomically" (ADR-003/009) and "RLS on every query" (ADR-006) mechanical.

## 1. Session & RLS

```python
# shared/persistence/session.py
engine = create_async_engine(settings.database.dsn.get_secret_value(),
                             pool_size=..., pool_pre_ping=True,
                             connect_args={"options": "-c statement_timeout=30000"})

@asynccontextmanager
async def tenant_session(principal: Principal) -> AsyncIterator[AsyncSession]:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        async with session.begin():
            # RLS: every transaction stamps the tenant; policies read this GUC.
            await session.execute(
                text("SELECT set_config('app.tenant_id', :t, true)"),  # true = txn-local
                {"t": str(principal.tenant_id)})
            yield session
```

- `set_config(..., true)` is **transaction-local** — no leakage across pooled connections (the classic RLS-with-pooling bug).
- The app's DB role has RLS `FORCE`d and no `BYPASSRLS`; migrations run under a separate migration role.
- A session without tenant config can only see zero rows — fail-closed by construction; platform-level operations (cross-tenant admin, outbox relay) use an explicitly-granted `platform` role via a separate, audited code path.

## 2. The Audited UoW — the only mutation path

```python
# shared/persistence/uow.py
class AuditedUnitOfWork:
    """One atomic business action: mutations + audit event(s) + outbox event(s).
    Constructed per service call; commit() is called exactly once, here and only here."""

    def __init__(self, session: AsyncSession, actor: Actor, serializer_v: str = AUDIT_SER_V):
        self._s = session; self._actor = actor
        self._audits: list[AuditDraft] = []; self._events: list[DomainEvent] = []

    def record(self, action: str, subject: SubjectRef,
               before: Mapping | None, after: Mapping | None) -> None:
        self._audits.append(AuditDraft(action, subject, before, after))

    def publish(self, event: DomainEvent) -> None:
        self._events.append(event)          # buffered — nothing leaves before commit

    async def commit(self) -> None:
        if not self._audits:
            raise UnauditedMutationError()   # writing without recording is a bug, loudly
        prev = await self._chain_tip_locked()          # per-tenant tip, FOR UPDATE (ADR-009)
        for d in self._audits:
            payload = canonical_json(d, self._actor, self._serializer_v)
            prev = sha256(prev + payload)
            self._s.add(AuditEvent(payload=payload, event_hash=prev,
                                   actor=self._actor.ref, serializer_v=self._serializer_v))
        for e in self._events:
            self._s.add(OutboxEvent(event_id=e.event_id, type=e.type,
                                    payload=e.model_dump_json(), trace=otel_carrier()))
        await self._s.commit()
```

Service usage pattern (normative):

```python
class ApprovalService:
    async def grant(self, wid: UUID, body: ApprovalRequest, ctx: AuthzContext) -> ApprovalOut:
        async with tenant_session(ctx.principal) as s:
            uow = AuditedUnitOfWork(s, ctx.actor)
            wi = await WorkItemRepo(s).get_for_update(wid)      # row lock
            check_abac(policies.can_approve, ctx, wi)           # SoD, scope, state — raises
            if body.content_hash != wi.current_content_hash():
                raise StaleApprovalError()
            approval = wi.grant_approval(ctx.actor, body)       # domain logic on the aggregate
            uow.record("approval.granted", wi.ref(),
                       before={"status": "AWAITING_HUMAN_REVIEW"},
                       after={"status": "APPROVED", "content_hash": body.content_hash})
            uow.publish(ApprovalGranted(subject=wi.ref(), approver=ctx.actor.ref,
                                        content_hash=body.content_hash))
            await uow.commit()
            return ApprovalOut.from_domain(approval)
```

Enforcement: `session.commit()` outside `shared/persistence/` is lint-banned (doc 01 §2); integration tests include the **invariant test** — attempt a mutation with a UoW carrying no audit draft and assert `UnauditedMutationError`; attempt a crash between flush and commit and assert neither state, audit, nor outbox rows survive.

## 3. Repositories & models

- SQLAlchemy 2.0 style (typed `Mapped[]`, `mapped_column`), async throughout; models module-private (doc 02 §2).
- Every business table: `tenant_id` (NOT NULL, RLS policy), `id` (UUIDv7 — time-ordered, index-friendly), `created_at/created_by`; mutable tables add `updated_at/updated_by` + `version_id` (optimistic locking → ETags, mapper `version_id_col`).
- Immutable tables (`computation`, `approval`, `audit_event`, `rule_pack`, published `batch`) get DB-level guards: `REVOKE UPDATE, DELETE` from the app role + trigger raising on UPDATE — beliefs about immutability are enforced twice (doc 04 §3, Phase 2).
- Repositories expose intention-named queries (`get_for_update`, `list_open_for_entity`), return domain-shaped results, and never leak `Select` objects upward. Cross-module data access = the other module's service, never its repo (import-linter enforced).

## 4. Money & precision

`Numeric(18, 4)` columns ↔ `decimal.Decimal` end-to-end; currency always alongside amount (`Money` value type in contracts: `amount_minor: int` + `currency: str` on the wire, `Decimal` internally with explicit quantize at pack-defined rounding points only). The engine's rounding rules live in packs (ADR-005); nowhere else may call `.quantize` on tax figures — grep-able rule.

## 5. Alembic discipline

- **One linear history** (no branches; merge conflicts in revision graph = rebase, not merge-heads).
- Every revision: `upgrade()` + real `downgrade()` (tested in CI: upgrade → downgrade → upgrade on empty + seeded DB).
- **Expand → migrate → contract** for anything touching live tables (Phase 2 doc 08 §3): additive revision ships with release N, backfill task + dual-write if needed, contraction ships ≥ N+1 — rollback never fights schema.
- Autogenerate is a draft, not an author: hand-review required for RLS policies, triggers, `REVOKE`s, partitions, and indexes (autogen misses most of these); `just migrate` wraps autogenerate + a checklist prompt.
- RLS policies, audit triggers, and partition DDL live in migrations as explicit `op.execute` blocks with comments citing the ADR they implement — schema archaeology should read like the architecture docs.
