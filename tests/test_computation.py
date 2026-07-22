"""US-301 / US-202 against the database: snapshots, idempotence, lineage drill-down."""

import hashlib
import uuid
from datetime import date
from decimal import Decimal

import pytest
from taxos_core.compliance.service import ComputationService, NoValidatedDataError
from taxos_core.ingestion.models import Batch, BatchStatus, TransactionRow
from taxos_core.ingestion.service import IngestionService
from taxos_core.masterdata.service import EntityService
from taxos_core.shared.persistence.uow import Actor

ACTOR = Actor.user("daniel@dev")

# A UK Corporation Tax computation: profit before tax, add-backs, then reliefs.
# TTP = 800000 + (120000 + 15000) - (200000 + 90000) = 645000; CT @ 25% = 161250.
CT_LINES = [
    ("PBT", "CT-PBT", "800000.00"),
    ("DEP", "CT-DEP", "120000.00"),
    ("ENT", "CT-ENT", "15000.00"),
    ("CAP", "CT-CAP", "200000.00"),
    ("RDE", "CT-RDE", "90000.00"),
]


async def _seed_ct_batch(session, tenant_id, entity_id, period_key="2026"):  # noqa: ANN001
    """Insert a validated Corporation Tax adjustment batch directly. CT adjustments are not
    VAT-shaped rows, so they do not flow through VAT ingestion — they are their own feed."""
    batch = Batch(
        tenant_id=tenant_id,
        entity_id=entity_id,
        period_key=period_key,
        source_type="CT",
        filename="ct.csv",
        content_hash=hashlib.sha256(f"ct-{entity_id}-{period_key}".encode()).hexdigest(),
        status=BatchStatus.VALIDATED,
        row_count=len(CT_LINES),
        accepted_count=len(CT_LINES),
        quarantined_count=0,
        created_by=ACTOR.ref,
    )
    session.add(batch)
    await session.flush()
    for index, (code, ref, amount) in enumerate(CT_LINES, start=1):
        session.add(
            TransactionRow(
                tenant_id=tenant_id,
                batch_id=batch.id,
                row_number=index,
                row_hash=hashlib.sha256(f"{ref}{amount}".encode()).hexdigest(),
                document_ref=ref,
                document_date=date(2026, 3, 31),
                counterparty="CT adjustment",
                net_amount=Decimal(amount),
                vat_amount=Decimal("0.00"),
                vat_code=code,
                currency="GBP",
                source_payload={},
            )
        )
    await session.commit()
    return batch


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


# --- AP-3: a second tax type on the same engine, persistence and audit --------


async def test_corporation_tax_computes_through_the_same_pipeline(session_a, tenant_a):
    """The proof the platform is tax-type-agnostic: CT is authored as a pack, and the same
    ComputationService that files VAT produces a Corporation Tax charge — snapshot, lineage,
    audit and all — with no VAT-specific path involved."""
    entity = await EntityService(session_a, tenant_a, ACTOR).create_entity(
        code="UK-CT", name="Meridian UK Ltd", jurisdiction_code="UK"
    )
    await _seed_ct_batch(session_a, tenant_a, entity.id)

    computation = await ComputationService(session_a, tenant_a, ACTOR).compute_corporation_tax(
        entity_id=entity.id, period_key="2026"
    )

    assert computation.tax_type == "CT"
    assert computation.pack_ref == "uk-corporation-tax@1.0.0"
    assert Decimal(computation.result["box_ttp"]) == Decimal("645000.00")
    assert Decimal(computation.result["box_ct"]) == Decimal("161250.00")


async def test_ct_lineage_drills_from_the_charge_to_the_adjustments(session_a, tenant_a):
    """Corporation Tax gets the same evidence trail as VAT for free — the add-backs box
    reconciles to the depreciation and entertaining lines, each carrying its citation."""
    entity = await EntityService(session_a, tenant_a, ACTOR).create_entity(
        code="UK-CT2", name="Meridian UK Ltd", jurisdiction_code="UK"
    )
    await _seed_ct_batch(session_a, tenant_a, entity.id)
    svc = ComputationService(session_a, tenant_a, ACTOR)
    computation = await svc.compute_corporation_tax(entity_id=entity.id, period_key="2026")

    addbacks = await svc.get_lineage(computation.id, "box_addbacks")
    assert {e.document_ref for e in addbacks} == {"CT-DEP", "CT-ENT"}
    total = sum((e.amount for e in addbacks), Decimal("0"))
    assert total == Decimal(computation.result["box_addbacks"])
    assert all(e.citation_ref for e in addbacks)
    assert any("CTA 2009 s.1298" in e.citation_ref for e in addbacks)


async def test_vat_and_ct_do_not_mix_even_in_the_same_period(session_a, tenant_a, prepared_entity):
    """The source-type filter, proven: an entity with both a VAT quarter and a CT batch in
    the SAME period key computes each return from only its own feed. A VAT figure never
    absorbs a Corporation Tax adjustment, and vice versa."""
    # prepared_entity already has AR/AP batches for 2026-Q2. Add a CT batch for 2026-Q2 too,
    # so only the source type — not the period — separates them.
    await _seed_ct_batch(session_a, tenant_a, prepared_entity, period_key="2026-Q2")
    svc = ComputationService(session_a, tenant_a, ACTOR)

    vat = await svc.compute_vat(entity_id=prepared_entity, period_key="2026-Q2")
    assert vat.tax_type == "VAT"
    assert Decimal(vat.result["box_1"]) == Decimal("3800.00")  # unchanged by the CT rows
    assert "box_ct" not in vat.result

    ct = await svc.compute_corporation_tax(entity_id=prepared_entity, period_key="2026-Q2")
    assert ct.tax_type == "CT"
    assert Decimal(ct.result["box_ct"]) == Decimal("161250.00")
    assert "box_1" not in ct.result
