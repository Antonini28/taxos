"""US-603: the evidence pack — the audit-ready download.

The pack is the whole thesis made tangible, so its guarantees get tested: it refuses to
assemble for an unapproved item, it verifies the chain as it builds, and it contains the
figures, their lineage, the approval with its content hash, and the agent trace.
"""

import pytest
from taxos_core.compliance.service import ComputationService
from taxos_core.ingestion.service import IngestionService
from taxos_core.masterdata.service import EntityService
from taxos_core.reporting.evidence import EvidenceService, NotApprovedError, render_html
from taxos_core.risk.service import RiskService
from taxos_core.shared.persistence.uow import Actor
from taxos_core.workflow.service import WorkflowService
from taxos_core.workflow.states import WorkItemState

PREPARER = Actor.user("daniel@dev")
REVIEWER = Actor.user("priya@dev")


@pytest.fixture
async def approved_item(session_a, tenant_a):
    """A fully prepared and approved VAT return — the state an evidence pack needs."""
    from tests.test_computation import PURCHASE_CSV, SALES_CSV

    entity = await EntityService(session_a, tenant_a, PREPARER).create_entity(
        code="UK-01", name="Meridian UK Ltd", jurisdiction_code="UK"
    )
    ingestion = IngestionService(session_a, tenant_a, PREPARER)
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
    computation = await ComputationService(session_a, tenant_a, PREPARER).compute_vat(
        entity_id=entity.id, period_key="2026-Q2"
    )
    await RiskService(session_a, tenant_a, PREPARER).scan(entity_id=entity.id, period_key="2026-Q2")

    workflow = WorkflowService(session_a, tenant_a, PREPARER)
    item = await workflow.create_work_item(
        entity_id=entity.id,
        period_key="2026-Q2",
        item_type="VAT_RETURN",
        title="Meridian UK · VAT Q2-2026",
        computation_id=computation.id,
    )
    item = await workflow.transition(item.id, WorkItemState.AWAITING_REVIEW)
    await WorkflowService(session_a, tenant_a, REVIEWER).approve(
        item.id, content_hash=item.content_hash, comment="Lineage checked."
    )
    return item.id


async def test_pack_assembles_for_an_approved_item(session_a, tenant_a, approved_item):
    pack = await EvidenceService(session_a, tenant_a, REVIEWER).build(approved_item)

    assert pack.chain_verified is True
    assert pack.chain_events > 0
    assert pack.boxes  # the 9 boxes
    assert pack.lineage  # at least one box drills to transactions
    assert pack.approvals and pack.approvals[0]["approver"] == "user:priya@dev"
    assert pack.approvals[0]["content_hash"]


async def test_pack_refuses_an_unapproved_item(session_a, tenant_a):
    entity = await EntityService(session_a, tenant_a, PREPARER).create_entity(
        code="UK-05", name="Draft Ltd", jurisdiction_code="UK"
    )
    item = await WorkflowService(session_a, tenant_a, PREPARER).create_work_item(
        entity_id=entity.id, period_key="2026-Q2", item_type="VAT_RETURN", title="Draft"
    )
    with pytest.raises(NotApprovedError, match="only produced for an APPROVED"):
        await EvidenceService(session_a, tenant_a, PREPARER).build(item.id)


async def test_pack_includes_lineage_that_reconciles(session_a, tenant_a, approved_item):
    from decimal import Decimal

    pack = await EvidenceService(session_a, tenant_a, REVIEWER).build(approved_item)
    box_values = {b["box_id"]: Decimal(b["value"]) for b in pack.boxes}

    for box_id, entries in pack.lineage.items():
        total = sum(Decimal(x["amount"]) for x in entries)
        assert total.quantize(Decimal("0.01")) == box_values[box_id].quantize(Decimal("0.01")), (
            f"{box_id} lineage in the pack does not reconcile"
        )


async def test_pack_names_the_hmrc_authority_for_each_figure(session_a, tenant_a, approved_item):
    pack = await EvidenceService(session_a, tenant_a, REVIEWER).build(approved_item)
    citations = {x["citation_ref"] for entries in pack.lineage.values() for x in entries}
    assert citations  # every contributing line carries its authority
    assert any("VAT" in c for c in citations)


async def test_rendered_html_is_self_contained_and_shows_verification(
    session_a, tenant_a, approved_item
):
    pack = await EvidenceService(session_a, tenant_a, REVIEWER).build(approved_item)
    document = render_html(pack)

    assert document.startswith("<!doctype html>")
    assert "Audit chain verified" in document
    assert "http://" not in document.replace("lang=", "")  # no external assets
    assert "src=" not in document  # nothing loaded from elsewhere
    assert pack.approvals[0]["content_hash"] in document  # the binding is in the pack


@pytest.fixture
async def approved_ct_item(session_a, tenant_a):
    """A prepared and approved Corporation Tax computation — the same lifecycle as VAT, on a
    different tax type, so the whole governed pipeline is proven tax-agnostic (AP-3)."""
    from tests.test_computation import _seed_ct_batch

    entity = await EntityService(session_a, tenant_a, PREPARER).create_entity(
        code="UK-CT", name="Meridian UK Ltd", jurisdiction_code="UK"
    )
    await _seed_ct_batch(session_a, tenant_a, entity.id)
    computation = await ComputationService(session_a, tenant_a, PREPARER).compute_corporation_tax(
        entity_id=entity.id, period_key="2026"
    )

    workflow = WorkflowService(session_a, tenant_a, PREPARER)
    item = await workflow.create_work_item(
        entity_id=entity.id,
        period_key="2026",
        item_type="CT_COMPUTATION",
        title="Meridian UK · Corporation Tax FY2026",
        computation_id=computation.id,
    )
    item = await workflow.transition(item.id, WorkItemState.AWAITING_REVIEW)
    await WorkflowService(session_a, tenant_a, REVIEWER).approve(
        item.id, content_hash=item.content_hash, comment="Adjustments agreed to the accounts."
    )
    return item.id


async def test_corporation_tax_gets_the_same_evidence_pack_as_vat(
    session_a, tenant_a, approved_ct_item
):
    """The audit-ready download works for Corporation Tax with no CT-specific evidence code:
    the pack carries the derived charge, the lineage reconciles, and every figure is cited."""
    from decimal import Decimal

    pack = await EvidenceService(session_a, tenant_a, REVIEWER).build(approved_ct_item)

    assert pack.chain_verified is True
    box_values = {b["box_id"]: Decimal(b["value"]) for b in pack.boxes}
    assert box_values["box_ct"] == Decimal("161250.00")

    for box_id, entries in pack.lineage.items():
        total = sum(Decimal(x["amount"]) for x in entries)
        assert total.quantize(Decimal("0.01")) == box_values[box_id].quantize(Decimal("0.01"))

    citations = {x["citation_ref"] for entries in pack.lineage.values() for x in entries}
    assert any("CTA 2009" in c for c in citations)

    document = render_html(pack)
    assert document.startswith("<!doctype html>")
    assert "Corporation Tax" in document  # the item title carries through
    assert pack.approvals[0]["content_hash"] in document


async def test_pack_carries_the_agent_trace_when_agent_prepared(session_a, tenant_a):
    """An agent-prepared item's pack includes the run's steps — the FR-302 trace as evidence."""
    from taxos_core.agents.supervisor import Supervisor

    from tests.test_computation import PURCHASE_CSV, SALES_CSV

    entity = await EntityService(session_a, tenant_a, PREPARER).create_entity(
        code="UK-07", name="Agent Prepared Ltd", jurisdiction_code="UK"
    )
    ingestion = IngestionService(session_a, tenant_a, PREPARER)
    await ingestion.ingest_csv(
        entity_id=entity.id,
        period_key="2026-Q2",
        source_type="AR",
        filename="s.csv",
        content=SALES_CSV,
    )
    await ingestion.ingest_csv(
        entity_id=entity.id,
        period_key="2026-Q2",
        source_type="AP",
        filename="p.csv",
        content=PURCHASE_CSV,
    )
    supervisor = Supervisor(session_a, tenant_a, PREPARER)
    run = await supervisor.start_vat_run(entity_id=entity.id, period_key="2026-Q2")
    outcome = await supervisor.execute(run.id)

    await WorkflowService(session_a, tenant_a, REVIEWER).approve(
        outcome.run.work_item_id,
        content_hash=(
            await WorkflowService(session_a, tenant_a, REVIEWER).get(outcome.run.work_item_id)
        ).content_hash,
    )

    pack = await EvidenceService(session_a, tenant_a, REVIEWER).build(outcome.run.work_item_id)
    assert pack.agent_steps
    assert {s["agent"] for s in pack.agent_steps} >= {"data", "vat"}
