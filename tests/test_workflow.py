"""US-402 acceptance criteria: the approval gate.

Mirrors the Gherkin in docs/discovery/06 — state change requires a named approver,
self-approval is blocked, and a later input change voids the approval.
"""

import uuid

import pytest
from sqlalchemy import text
from taxos_core.compliance.service import ComputationService
from taxos_core.ingestion.service import IngestionService
from taxos_core.masterdata.service import EntityService
from taxos_core.shared.persistence.uow import Actor
from taxos_core.workflow.service import (
    NotReviewableError,
    SegregationOfDutiesError,
    StaleContentError,
    WorkflowService,
)
from taxos_core.workflow.states import TransitionError, WorkItemState

from tests.test_computation import PURCHASE_CSV, SALES_CSV

PREPARER = Actor.user("daniel@dev")
REVIEWER = Actor.user("priya@dev")

EXTRA_SALES = (
    b"document_ref,document_date,counterparty,net_amount,vat_amount,vat_code,currency\n"
    b"SI-009,2026-06-20,Late Invoice Ltd,5000.00,1000.00,S20,GBP\n"
)


@pytest.fixture
async def review_ready(session_a, tenant_a):
    """A work item sitting in AWAITING_REVIEW, prepared by daniel."""
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
    workflow = WorkflowService(session_a, tenant_a, PREPARER)
    item = await workflow.create_work_item(
        entity_id=entity.id,
        period_key="2026-Q2",
        item_type="VAT_RETURN",
        title="UK-01 · VAT Q2-2026",
        computation_id=computation.id,
    )
    item = await workflow.transition(item.id, WorkItemState.AWAITING_REVIEW)
    return item, entity.id, computation


# --- Scenario: state change requires a named approver -------------------------


async def test_reviewer_can_approve_and_identity_is_recorded(session_a, tenant_a, review_ready):
    item, _, _ = review_ready
    reviewer_service = WorkflowService(session_a, tenant_a, REVIEWER)

    outcome = await reviewer_service.approve(
        item.id, content_hash=item.content_hash, comment="Checked lineage on box 4."
    )

    assert outcome.work_item.state == WorkItemState.APPROVED
    assert outcome.approval.approver == "user:priya@dev"
    assert outcome.approval.content_hash == item.content_hash
    assert outcome.approval.comment == "Checked lineage on box 4."
    assert outcome.approval.voided is False


# --- Scenario: self-approval is blocked ---------------------------------------


async def test_preparer_cannot_approve_own_work(session_a, tenant_a, review_ready):
    """Segregation of duties, enforced — not configurable, not overridable."""
    item, _, _ = review_ready
    preparer_service = WorkflowService(session_a, tenant_a, PREPARER)

    with pytest.raises(SegregationOfDutiesError, match="second reviewer"):
        await preparer_service.approve(item.id, content_hash=item.content_hash)


async def test_can_approve_explains_why_not(session_a, tenant_a, review_ready):
    """The UI shows a reason rather than a dead button."""
    item, _, _ = review_ready

    allowed, reason = await WorkflowService(session_a, tenant_a, PREPARER).can_approve(item.id)
    assert allowed is False
    assert "prepared this item" in reason

    allowed, reason = await WorkflowService(session_a, tenant_a, REVIEWER).can_approve(item.id)
    assert allowed is True and reason is None


# --- Scenario: approval binds to content --------------------------------------


async def test_approving_a_stale_hash_is_refused(session_a, tenant_a, review_ready):
    item, _, _ = review_ready
    with pytest.raises(StaleContentError, match="changed since you opened"):
        await WorkflowService(session_a, tenant_a, REVIEWER).approve(item.id, content_hash="0" * 64)


async def test_input_change_voids_the_approval_and_reopens_the_item(
    session_a, tenant_a, review_ready
):
    """The heart of US-402: new data means the approval no longer attests to reality."""
    item, entity_id, _ = review_ready
    reviewer_service = WorkflowService(session_a, tenant_a, REVIEWER)
    await reviewer_service.approve(item.id, content_hash=item.content_hash)

    # New sales data arrives and is recomputed — the figures move.
    await IngestionService(session_a, tenant_a, PREPARER).ingest_csv(
        entity_id=entity_id,
        period_key="2026-Q2",
        source_type="AR",
        filename="late_sales.csv",
        content=EXTRA_SALES,
    )
    new_computation = await ComputationService(session_a, tenant_a, PREPARER).compute_vat(
        entity_id=entity_id, period_key="2026-Q2"
    )
    await WorkflowService(session_a, tenant_a, PREPARER).attach_computation(
        item.id, new_computation.id
    )

    revalidated = await reviewer_service.revalidate(item.id)

    assert revalidated.state == WorkItemState.DRAFT
    approvals = await reviewer_service.approvals(item.id)
    assert len(approvals) == 1
    assert approvals[0].voided is True
    assert "changed after approval" in approvals[0].void_reason


async def test_revalidate_leaves_an_unchanged_approval_alone(session_a, tenant_a, review_ready):
    """Re-checking must not churn: identical content keeps the approval standing."""
    item, _, _ = review_ready
    service = WorkflowService(session_a, tenant_a, REVIEWER)
    await service.approve(item.id, content_hash=item.content_hash)

    unchanged = await service.revalidate(item.id)
    assert unchanged.state == WorkItemState.APPROVED
    assert (await service.approvals(item.id))[0].voided is False


# --- state machine -------------------------------------------------------------


async def test_illegal_transitions_are_refused_with_an_explanation(
    session_a, tenant_a, review_ready
):
    item, _, _ = review_ready
    service = WorkflowService(session_a, tenant_a, PREPARER)
    await service.transition(item.id, WorkItemState.CANCELLED)

    with pytest.raises(TransitionError) as exc:
        await service.transition(item.id, WorkItemState.AWAITING_REVIEW)
    assert "Cannot move work item from CANCELLED" in str(exc.value)


async def test_approval_requires_awaiting_review_state(session_a, tenant_a, review_ready):
    item, _, _ = review_ready
    await WorkflowService(session_a, tenant_a, PREPARER).transition(
        item.id, WorkItemState.CHANGES_REQUESTED, comment="Please explain the Q2 variance"
    )
    with pytest.raises(NotReviewableError, match="only items awaiting review"):
        await WorkflowService(session_a, tenant_a, REVIEWER).approve(
            item.id, content_hash=item.content_hash
        )


async def test_history_records_every_transition_with_its_actor(session_a, tenant_a, review_ready):
    item, _, _ = review_ready
    service = WorkflowService(session_a, tenant_a, REVIEWER)
    await service.approve(item.id, content_hash=item.content_hash, comment="Approved")

    history = await service.history(item.id)
    assert [(t.from_state, t.to_state) for t in history] == [
        (WorkItemState.DRAFT, WorkItemState.AWAITING_REVIEW),
        (WorkItemState.AWAITING_REVIEW, WorkItemState.APPROVED),
    ]
    assert history[0].actor == "user:daniel@dev"
    assert history[1].actor == "user:priya@dev"


# --- immutability & audit -------------------------------------------------------


async def test_approval_facts_cannot_be_rewritten(session_a, tenant_a, review_ready):
    item, _, _ = review_ready
    await WorkflowService(session_a, tenant_a, REVIEWER).approve(
        item.id, content_hash=item.content_hash
    )
    with pytest.raises(Exception, match="immutable"):
        await session_a.execute(text("UPDATE approval SET approver = 'user:attacker'"))
    await session_a.rollback()


async def test_a_voided_approval_cannot_be_resurrected(session_a, tenant_a, review_ready):
    item, entity_id, _ = review_ready
    service = WorkflowService(session_a, tenant_a, REVIEWER)
    await service.approve(item.id, content_hash=item.content_hash)
    await session_a.execute(text("UPDATE approval SET voided = true, void_reason = 'test'"))
    with pytest.raises(Exception, match="cannot be un-voided"):
        await session_a.execute(text("UPDATE approval SET voided = false"))
    await session_a.rollback()


async def test_approval_is_audited_and_chain_still_verifies(session_a, tenant_a, review_ready):
    from sqlalchemy import select
    from taxos_core.audit.models import AuditEvent
    from taxos_core.audit.verify import verify_chain

    item, _, _ = review_ready
    await WorkflowService(session_a, tenant_a, REVIEWER).approve(
        item.id, content_hash=item.content_hash, comment="ok"
    )

    events = (
        (await session_a.execute(select(AuditEvent).where(AuditEvent.action == "approval.granted")))
        .scalars()
        .all()
    )
    assert len(events) == 1
    assert events[0].actor == "user:priya@dev"
    assert events[0].after["content_hash"] == item.content_hash
    assert (await verify_chain(session_a, tenant_a)).verified is True


async def test_work_items_are_tenant_isolated(
    session_a, session_b, tenant_a, tenant_b, review_ready
):
    from sqlalchemy import select
    from taxos_core.workflow.models import WorkItem

    assert (await session_b.execute(select(WorkItem))).scalars().all() == []
    assert len(await WorkflowService(session_a, tenant_a, REVIEWER).list_items()) == 1


async def test_agent_prepared_items_credit_the_requesting_human(session_a, tenant_a):
    """An agent cannot be a party to segregation of duties: the human who asked for the
    work owns preparation, so the SoD check still has two real people to compare."""
    entity = await EntityService(session_a, tenant_a, PREPARER).create_entity(
        code="UK-07", name="Agent Prepared Ltd", jurisdiction_code="UK"
    )
    agent = Actor.agent("vat", uuid.uuid4())
    item = await WorkflowService(session_a, tenant_a, agent).create_work_item(
        entity_id=entity.id,
        period_key="2026-Q2",
        item_type="VAT_RETURN",
        title="Agent run",
        prepared_by=PREPARER.ref,
    )
    assert item.prepared_by == "user:daniel@dev"
    assert item.created_by.startswith("agent:vat:run:")

    allowed, reason = await WorkflowService(session_a, tenant_a, PREPARER).can_approve(item.id)
    assert allowed is False  # still cannot approve what they asked for
