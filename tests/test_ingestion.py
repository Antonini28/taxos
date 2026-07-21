"""US-201 acceptance criteria, executable.

Mirrors the Gherkin in docs/discovery/06: valid batch accepted, invalid rows
quarantined (not dropped), duplicate upload rejected.
"""

import uuid
from decimal import Decimal

import pytest
from taxos_core.ingestion.models import BatchStatus, TransactionRow
from taxos_core.ingestion.service import DuplicateBatchError, IngestionService, period_bounds
from taxos_core.masterdata.service import EntityService
from taxos_core.shared.persistence.uow import Actor

ACTOR = Actor.user("daniel@dev")


@pytest.fixture
async def entity_id(session_a, tenant_a) -> uuid.UUID:
    entity = await EntityService(session_a, tenant_a, ACTOR).create_entity(
        code="UK-01", name="Meridian UK Ltd", jurisdiction_code="UK"
    )
    return entity.id


def test_period_bounds_are_explicit():
    assert period_bounds("2026-Q2") == (
        __import__("datetime").date(2026, 4, 1),
        __import__("datetime").date(2026, 6, 30),
    )
    assert period_bounds("2024-Q1")[1].day == 31


async def test_valid_batch_is_accepted(session_a, tenant_a, entity_id, clean_csv):
    """Scenario: Valid batch is accepted."""
    svc = IngestionService(session_a, tenant_a, ACTOR)
    report = await svc.ingest_csv(
        entity_id=entity_id,
        period_key="2026-Q2",
        source_type="AP",
        filename="ap_q2.csv",
        content=clean_csv,
    )
    assert report.status == BatchStatus.VALIDATED
    assert report.row_count == 4
    assert report.accepted_count == 4
    assert report.quarantined_count == 0
    assert report.control_total == Decimal("8300.00")  # net + vat across all rows


async def test_invalid_rows_are_quarantined_not_dropped(session_a, tenant_a, entity_id, dirty_csv):
    """Scenario: Invalid rows are quarantined, not silently dropped — with rule-level reasons."""
    svc = IngestionService(session_a, tenant_a, ACTOR)
    report = await svc.ingest_csv(
        entity_id=entity_id,
        period_key="2026-Q2",
        source_type="AP",
        filename="ap_q2_dirty.csv",
        content=dirty_csv,
    )
    assert report.status == BatchStatus.VALIDATED_WITH_EXCEPTIONS
    assert report.accepted_count == 1
    assert report.quarantined_count == 5

    # Every failure class was identified by its own rule id
    assert set(report.rule_breakdown) == {"ING-001", "ING-003", "ING-004", "ING-005", "ING-006"}

    quarantined = await svc.list_quarantine(report.batch_id)
    assert len(quarantined) == 5
    # Reasons are human-readable and name the offending field
    reasons = [f for row in quarantined for f in row.failures]
    assert all(r["message"] and r["rule"] for r in reasons)
    assert any("Unknown VAT code" in r["message"] for r in reasons)


async def test_quarantined_rows_never_reach_the_validated_set(
    session_a, tenant_a, entity_id, dirty_csv
):
    """The module's core invariant: no unvalidated row is available to computation."""
    from sqlalchemy import select

    svc = IngestionService(session_a, tenant_a, ACTOR)
    report = await svc.ingest_csv(
        entity_id=entity_id,
        period_key="2026-Q2",
        source_type="AP",
        filename="ap_q2_dirty.csv",
        content=dirty_csv,
    )
    rows = (await session_a.execute(select(TransactionRow))).scalars().all()
    assert len(rows) == 1
    assert rows[0].document_ref == "INV-010"
    assert await svc.count_validated_rows(report.batch_id) == 1


async def test_duplicate_batch_upload_is_rejected(session_a, tenant_a, entity_id, clean_csv):
    """Scenario: Duplicate batch upload is rejected — by content hash, not filename."""
    svc = IngestionService(session_a, tenant_a, ACTOR)
    first = await svc.ingest_csv(
        entity_id=entity_id,
        period_key="2026-Q2",
        source_type="AP",
        filename="ap_q2.csv",
        content=clean_csv,
    )
    with pytest.raises(DuplicateBatchError) as exc:
        await svc.ingest_csv(
            entity_id=entity_id,
            period_key="2026-Q2",
            source_type="AP",
            filename="renamed_but_identical.csv",
            content=clean_csv,
        )
    assert exc.value.original_batch_id == first.batch_id


async def test_same_content_allowed_in_a_different_period(
    session_a, tenant_a, entity_id, clean_csv
):
    """Dedupe is scoped to the period — identical monthly files in different
    quarters are legitimate."""
    svc = IngestionService(session_a, tenant_a, ACTOR)
    await svc.ingest_csv(
        entity_id=entity_id,
        period_key="2026-Q2",
        source_type="AP",
        filename="ap.csv",
        content=clean_csv,
    )
    report = await svc.ingest_csv(
        entity_id=entity_id,
        period_key="2026-Q3",
        source_type="AP",
        filename="ap.csv",
        content=clean_csv,
    )
    # Rows fall outside Q3, so they quarantine — but the batch itself was accepted for ingest
    assert report.row_count == 4


async def test_ingestion_is_audited_and_emits_events(session_a, tenant_a, entity_id, dirty_csv):
    """Ingestion rides the same audited path as everything else (no bypass for bulk work)."""
    from sqlalchemy import select
    from taxos_core.audit.models import AuditEvent
    from taxos_core.audit.verify import verify_chain
    from taxos_core.shared.events.models import OutboxEvent

    svc = IngestionService(session_a, tenant_a, ACTOR)
    await svc.ingest_csv(
        entity_id=entity_id,
        period_key="2026-Q2",
        source_type="AP",
        filename="ap_q2_dirty.csv",
        content=dirty_csv,
    )

    audits = (
        (await session_a.execute(select(AuditEvent).where(AuditEvent.action == "batch.ingested")))
        .scalars()
        .all()
    )
    assert len(audits) == 1
    assert audits[0].after["quarantined"] == 5
    assert audits[0].after["ruleset_version"]  # which rules judged this batch

    events = (await session_a.execute(select(OutboxEvent))).scalars().all()
    types = {e.type for e in events}
    assert {"BatchValidated", "RowsQuarantined"} <= types

    assert (await verify_chain(session_a, tenant_a)).verified is True


async def test_batch_identity_is_immutable(session_a, tenant_a, entity_id, clean_csv):
    """Rewriting which file/entity/period a batch came from would make lineage a lie."""
    from sqlalchemy import text

    svc = IngestionService(session_a, tenant_a, ACTOR)
    report = await svc.ingest_csv(
        entity_id=entity_id,
        period_key="2026-Q2",
        source_type="AP",
        filename="ap_q2.csv",
        content=clean_csv,
    )
    with pytest.raises(Exception, match="immutable"):
        await session_a.execute(
            text("UPDATE batch SET content_hash = 'rewritten' WHERE id = :id"),
            {"id": report.batch_id},
        )
    await session_a.rollback()


async def test_batches_are_tenant_isolated(
    session_a, session_b, tenant_a, tenant_b, entity_id, clean_csv
):
    """RLS covers the new tables too — proven, not assumed."""
    from sqlalchemy import select
    from taxos_core.ingestion.models import Batch

    await IngestionService(session_a, tenant_a, ACTOR).ingest_csv(
        entity_id=entity_id,
        period_key="2026-Q2",
        source_type="AP",
        filename="ap_q2.csv",
        content=clean_csv,
    )
    visible_to_b = (await session_b.execute(select(Batch))).scalars().all()
    assert visible_to_b == []
