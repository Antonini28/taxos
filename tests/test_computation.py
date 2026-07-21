"""US-301 / US-202 against the database: snapshots, idempotence, lineage drill-down."""

import uuid
from decimal import Decimal

import pytest
from taxos_core.compliance.service import ComputationService, NoValidatedDataError
from taxos_core.ingestion.service import IngestionService
from taxos_core.masterdata.service import EntityService
from taxos_core.shared.persistence.uow import Actor

ACTOR = Actor.user("daniel@dev")

SALES_CSV = (
    b"document_ref,document_date,counterparty,net_amount,vat_amount,vat_code,currency\n"
    b"SI-001,2026-04-10,Northwind Retail,10000.00,2000.00,S20,GBP\n"
    b"SI-002,2026-05-05,Cobalt Media,4000.00,800.00,S20,GBP\n"
    b"SI-003,2026-06-01,Health Trust,3000.00,0.00,E00,GBP\n"
)

PURCHASE_CSV = (
    b"document_ref,document_date,counterparty,net_amount,vat_amount,vat_code,currency\n"
    b"PI-001,2026-04-12,Apex Supplies Ltd,2000.00,400.00,S20,GBP\n"
    b"PI-002,2026-05-20,Delta Construction,5000.00,0.00,RC20,GBP\n"
)


@pytest.fixture
async def prepared_entity(session_a, tenant_a) -> uuid.UUID:
    """An entity with a validated quarter of sales and purchases."""
    entity = await EntityService(session_a, tenant_a, ACTOR).create_entity(
        code="UK-01", name="Meridian UK Ltd", jurisdiction_code="UK"
    )
    ingestion = IngestionService(session_a, tenant_a, ACTOR)
    await ingestion.ingest_csv(
        entity_id=entity.id,
        period_key="2026-Q2",
        source_type="AR",
        filename="sales.csv",
        content=SALES_CSV,
    )
    await ingestion.ingest_csv(
        entity_id=entity.id,
        period_key="2026-Q2",
        source_type="AP",
        filename="purchases.csv",
        content=PURCHASE_CSV,
    )
    return entity.id


async def test_computation_produces_a_pinned_snapshot(session_a, tenant_a, prepared_entity):
    svc = ComputationService(session_a, tenant_a, ACTOR)
    computation = await svc.compute_vat(entity_id=prepared_entity, period_key="2026-Q2")

    assert computation.pack_ref == "uk-vat@1.0.0"
    assert computation.engine_version == "1.0.0"
    assert len(computation.inputs_hash) == 64
    assert len(computation.result_hash) == 64
    assert len(computation.batch_ids) == 2

    # Sales VAT 2800 + reverse-charge self-account 1000 = 3800
    assert Decimal(computation.result["box_1"]) == Decimal("3800.00")
    # Input tax 400 + reverse-charge recovery 1000 = 1400
    assert Decimal(computation.result["box_4"]) == Decimal("1400.00")
    assert Decimal(computation.result["box_5"]) == Decimal("2400.00")


async def test_recomputation_is_idempotent(session_a, tenant_a, prepared_entity):
    """Same inputs, same pack ⇒ the existing snapshot, not a second one (FR-205)."""
    svc = ComputationService(session_a, tenant_a, ACTOR)
    first = await svc.compute_vat(entity_id=prepared_entity, period_key="2026-Q2")
    second = await svc.compute_vat(entity_id=prepared_entity, period_key="2026-Q2")
    assert first.id == second.id
    assert first.result_hash == second.result_hash


async def test_lineage_sums_exactly_to_the_box_value(session_a, tenant_a, prepared_entity):
    """US-202's acceptance criterion, verbatim: the sum of contributing amounts equals
    the box value exactly."""
    svc = ComputationService(session_a, tenant_a, ACTOR)
    computation = await svc.compute_vat(entity_id=prepared_entity, period_key="2026-Q2")

    for box_id in ("box_1", "box_4", "box_6", "box_7"):
        lineage = await svc.get_lineage(computation.id, box_id)
        total = sum((entry.amount for entry in lineage), Decimal("0"))
        assert total.quantize(Decimal("0.01")) == Decimal(computation.result[box_id]).quantize(
            Decimal("0.01")
        ), f"{box_id} lineage does not reconcile"


async def test_lineage_names_documents_and_citations(session_a, tenant_a, prepared_entity):
    """A reviewer sees which invoice, which counterparty, and under which authority."""
    svc = ComputationService(session_a, tenant_a, ACTOR)
    computation = await svc.compute_vat(entity_id=prepared_entity, period_key="2026-Q2")

    lineage = await svc.get_lineage(computation.id, "box_4")
    refs = {entry.document_ref for entry in lineage}
    assert {"PI-001", "PI-002"} <= refs
    assert all(entry.citation_ref for entry in lineage)

    reverse_charge = [entry for entry in lineage if entry.vat_code == "RC20"]
    assert reverse_charge and reverse_charge[0].amount == Decimal("1000.0000")


async def test_computation_is_audited_and_emits_event(session_a, tenant_a, prepared_entity):
    from sqlalchemy import select
    from taxos_core.audit.models import AuditEvent
    from taxos_core.audit.verify import verify_chain
    from taxos_core.shared.events.models import OutboxEvent

    svc = ComputationService(session_a, tenant_a, ACTOR)
    computation = await svc.compute_vat(entity_id=prepared_entity, period_key="2026-Q2")

    audit = (
        (
            await session_a.execute(
                select(AuditEvent).where(AuditEvent.action == "computation.completed")
            )
        )
        .scalars()
        .all()
    )
    assert len(audit) == 1
    assert audit[0].after["result_hash"] == computation.result_hash
    assert audit[0].after["pack"] == "uk-vat@1.0.0"

    events = (
        (
            await session_a.execute(
                select(OutboxEvent).where(OutboxEvent.type == "ComputationCompleted")
            )
        )
        .scalars()
        .all()
    )
    assert len(events) == 1

    assert (await verify_chain(session_a, tenant_a)).verified is True


async def test_computation_snapshot_is_immutable(session_a, tenant_a, prepared_entity):
    from sqlalchemy import text

    svc = ComputationService(session_a, tenant_a, ACTOR)
    computation = await svc.compute_vat(entity_id=prepared_entity, period_key="2026-Q2")

    with pytest.raises(Exception, match="append-only"):
        await session_a.execute(
            text("UPDATE computation SET result_hash = 'rewritten' WHERE id = :i"),
            {"i": computation.id},
        )
    await session_a.rollback()


async def test_no_validated_data_raises_rather_than_computing_zero(session_a, tenant_a):
    """An empty return and an unfiled return must not look alike."""
    entity = await EntityService(session_a, tenant_a, ACTOR).create_entity(
        code="UK-99", name="Dormant Ltd", jurisdiction_code="UK"
    )
    svc = ComputationService(session_a, tenant_a, ACTOR)
    with pytest.raises(NoValidatedDataError):
        await svc.compute_vat(entity_id=entity.id, period_key="2026-Q2")


async def test_quarantined_rows_are_excluded_from_the_computation(session_a, tenant_a, dirty_csv):
    """The ingestion invariant, proven end to end: quarantined rows change no figure."""
    entity = await EntityService(session_a, tenant_a, ACTOR).create_entity(
        code="UK-02", name="Meridian Services Ltd", jurisdiction_code="UK"
    )
    await IngestionService(session_a, tenant_a, ACTOR).ingest_csv(
        entity_id=entity.id,
        period_key="2026-Q2",
        source_type="AP",
        filename="dirty.csv",
        content=dirty_csv,
    )
    computation = await ComputationService(session_a, tenant_a, ACTOR).compute_vat(
        entity_id=entity.id, period_key="2026-Q2"
    )
    # Only the single clean row (net 1000, VAT 200 at S20) survived validation
    assert Decimal(computation.result["box_4"]) == Decimal("200.00")
    assert Decimal(computation.result["box_7"]) == Decimal("1000")
