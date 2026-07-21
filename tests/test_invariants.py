"""THE INVARIANT SUITE — the architecture, executable (Phase 6 doc 06 §3).

These tests encode guarantees from the ADRs. Breaking one is definitionally an
architecture change requiring an ADR update, not a test fix. They never get skipped.
"""

from datetime import date

import pytest
from sqlalchemy import select, text
from taxos_core.audit.models import AuditEvent
from taxos_core.audit.verify import verify_chain
from taxos_core.masterdata.models import LegalEntity
from taxos_core.masterdata.service import EntityService
from taxos_core.shared.events.models import OutboxEvent
from taxos_core.shared.persistence.uow import Actor, AuditedUnitOfWork, UnauditedMutationError

ACTOR = Actor.user("daniel@dev")


# --- ADR-009: nothing changes state without attribution -----------------------


async def test_unaudited_mutation_cannot_commit(session_a, tenant_a):
    """A UoW that mutates without recording an audit draft must refuse to commit."""
    uow = AuditedUnitOfWork(session_a, tenant_a, ACTOR)
    session_a.add(
        LegalEntity(
            tenant_id=tenant_a,
            code="UK-99",
            name="Sneaky Ltd",
            jurisdiction_code="UK",
            created_by=ACTOR.ref,
        )
    )
    with pytest.raises(UnauditedMutationError):
        await uow.commit()


async def test_state_audit_and_outbox_commit_atomically(session_a, tenant_a):
    """One business action ⇒ business row + audit row + outbox row, all or nothing."""
    svc = EntityService(session_a, tenant_a, ACTOR)
    entity = await svc.create_entity(code="UK-01", name="Meridian UK Ltd", jurisdiction_code="UK")

    entities = (await session_a.execute(select(LegalEntity))).scalars().all()
    audits = (await session_a.execute(select(AuditEvent))).scalars().all()
    outbox = (await session_a.execute(select(OutboxEvent))).scalars().all()

    assert len(entities) == 1
    assert len(audits) == 1 and audits[0].subject_id == str(entity.id)
    assert len(outbox) == 1 and outbox[0].type == "EntityCreated"
    assert outbox[0].published_at is None  # nothing leaves before the relay publishes


async def test_audit_chain_verifies_across_multiple_actions(session_a, tenant_a):
    svc = EntityService(session_a, tenant_a, ACTOR)
    entity = await svc.create_entity(code="UK-01", name="Meridian UK Ltd", jurisdiction_code="UK")
    await svc.register_for_tax(
        entity_id=entity.id,
        tax_type="VAT",
        registration_number="GB123456789",
        effective_from=date(2026, 1, 1),
    )
    result = await verify_chain(session_a, tenant_a)
    assert result.verified is True
    assert result.events_checked == 2


async def test_audit_chain_detects_tampering(session_a, tenant_a, admin_engine):
    """Rewrite a payload behind the app's back — verification must localise the break."""
    svc = EntityService(session_a, tenant_a, ACTOR)
    await svc.create_entity(code="UK-01", name="Meridian UK Ltd", jurisdiction_code="UK")
    await svc.create_entity(code="UK-02", name="Meridian Services Ltd", jurisdiction_code="UK")

    # Bypass the trigger the way a compromised DBA would: disable it, alter, re-enable.
    # Requires owner privileges — which is precisely the insider this control targets.
    async with admin_engine.begin() as conn:
        await conn.execute(text("ALTER TABLE audit_event DISABLE TRIGGER audit_event_append_only"))
        await conn.execute(
            text(
                'UPDATE audit_event SET after = \'{"code": "TAMPERED"}\'::jsonb '
                "WHERE seq = (SELECT MIN(seq) FROM audit_event)"
            )
        )
        await conn.execute(text("ALTER TABLE audit_event ENABLE TRIGGER audit_event_append_only"))

    result = await verify_chain(session_a, tenant_a)
    assert result.verified is False
    assert result.broken_at_seq is not None
    assert "altered" in (result.reason or "")


async def test_audit_immutability_layer_1_privileges(session_a, tenant_a):
    """Layer 1 (grants): the application role has no UPDATE/DELETE on audit_event.

    Raw SQL from the app — the shape a compromised code path would take — is refused
    before any trigger is consulted.
    """
    svc = EntityService(session_a, tenant_a, ACTOR)
    await svc.create_entity(code="UK-01", name="Meridian UK Ltd", jurisdiction_code="UK")

    with pytest.raises(Exception, match="permission denied"):
        await session_a.execute(text("UPDATE audit_event SET actor = 'user:attacker'"))
    await session_a.rollback()

    with pytest.raises(Exception, match="permission denied"):
        await session_a.execute(text("DELETE FROM audit_event"))
    await session_a.rollback()


async def test_audit_immutability_layer_2_trigger(session_a, tenant_a, admin_engine):
    """Layer 2 (trigger): even the OWNER — who has every privilege — is refused.

    This is the layer that matters against a privileged insider; layer 1 alone would
    fall to anyone holding admin credentials.
    """
    svc = EntityService(session_a, tenant_a, ACTOR)
    await svc.create_entity(code="UK-01", name="Meridian UK Ltd", jurisdiction_code="UK")

    async with admin_engine.connect() as conn:
        with pytest.raises(Exception, match="append-only"):
            await conn.execute(text("UPDATE audit_event SET actor = 'user:attacker'"))
    async with admin_engine.connect() as conn:
        with pytest.raises(Exception, match="append-only"):
            await conn.execute(text("DELETE FROM audit_event"))


# --- ADR-006: tenant isolation is enforced by the database --------------------


async def test_rls_blocks_cross_tenant_read(session_a, session_b, tenant_a, tenant_b):
    """Tenant A's data is invisible to tenant B's session — no application filter involved."""
    await EntityService(session_a, tenant_a, ACTOR).create_entity(
        code="UK-01", name="Tenant A Entity", jurisdiction_code="UK"
    )
    visible_to_b = (await session_b.execute(select(LegalEntity))).scalars().all()
    assert visible_to_b == []

    visible_to_a = await EntityService(session_a, tenant_a, ACTOR).list_entities()
    assert len(visible_to_a) == 1


async def test_rls_blocks_cross_tenant_write(session_b, tenant_a, tenant_b):
    """Writing another tenant's id from a scoped session violates the policy's WITH CHECK."""
    session_b.add(
        LegalEntity(
            tenant_id=tenant_a,  # foreign tenant
            code="UK-XX",
            name="Cross-tenant write",
            jurisdiction_code="UK",
            created_by=ACTOR.ref,
        )
    )
    with pytest.raises(Exception, match="row-level security|violates"):
        await session_b.flush()
    await session_b.rollback()


async def test_audit_chains_are_per_tenant(session_a, session_b, tenant_a, tenant_b):
    """Tenants' chains are independent: A's events never appear in B's verification."""
    await EntityService(session_a, tenant_a, ACTOR).create_entity(
        code="UK-01", name="A Entity", jurisdiction_code="UK"
    )
    await EntityService(session_b, tenant_b, ACTOR).create_entity(
        code="UK-01", name="B Entity", jurisdiction_code="UK"
    )

    result_a = await verify_chain(session_a, tenant_a)
    result_b = await verify_chain(session_b, tenant_b)
    assert result_a.verified and result_a.events_checked == 1
    assert result_b.verified and result_b.events_checked == 1
    assert result_a.head_hash != result_b.head_hash


async def test_session_without_tenant_context_sees_nothing(clean_db, tenant_a):
    """Fail closed: an unscoped session is not a superuser session — it is a blind one."""
    from taxos_core.shared.persistence.session import platform_session, tenant_session

    async with tenant_session(tenant_a, engine=clean_db) as s:
        await EntityService(s, tenant_a, ACTOR).create_entity(
            code="UK-01", name="A Entity", jurisdiction_code="UK"
        )
    async with platform_session(engine=clean_db) as s:
        rows = (await s.execute(select(LegalEntity))).scalars().all()
    assert rows == []


# --- ADR-006 durability: new tables cannot forget their policy ----------------


async def test_every_business_table_has_rls_policy(clean_db):
    """Schema introspection: a tenant_id column without an RLS policy fails the build."""
    async with clean_db.connect() as conn:
        tables_with_tenant = {
            r[0]
            for r in await conn.execute(
                text(
                    "SELECT table_name FROM information_schema.columns "
                    "WHERE column_name = 'tenant_id' AND table_schema = 'public'"
                )
            )
        }
        tables_with_policy = {
            r[0] for r in await conn.execute(text("SELECT DISTINCT tablename FROM pg_policies"))
        }
    missing = tables_with_tenant - tables_with_policy
    assert not missing, f"tables with tenant_id but no RLS policy: {missing}"
