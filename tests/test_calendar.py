"""US-501: the filing calendar — derived obligations, statutory deadlines, live status.

The deadline functions are pure and pinned against HMRC's published dates. The service tests
prove the one property that matters: the calendar never disagrees with the workflow, because
its status IS the workflow state, read live.
"""

from datetime import date

from taxos_core.masterdata.service import EntityService
from taxos_core.reporting.calendar import (
    CalendarService,
    ObligationStatus,
    ct_filing_due_date,
    ct_period_end,
    vat_due_date,
)
from taxos_core.shared.persistence.uow import Actor
from taxos_core.workflow.service import WorkflowService
from taxos_core.workflow.states import WorkItemState

PREPARER = Actor.user("daniel@dev")
REVIEWER = Actor.user("priya@dev")


# --- statutory deadline arithmetic, pinned against HMRC's published dates ------


def test_vat_deadline_is_one_month_and_seven_days_after_the_period_end():
    """HMRC's own examples: a period ending 30 June is due 7 August; 31 March is due 7 May."""
    assert vat_due_date("2026-Q2") == date(2026, 8, 7)
    assert vat_due_date("2026-Q1") == date(2026, 5, 7)
    assert vat_due_date("2026-Q4") == date(2027, 2, 7)  # year rolls over


def test_ct_filing_deadline_is_twelve_months_after_the_period_end():
    assert ct_period_end("2026") == date(2026, 3, 31)
    assert ct_filing_due_date(date(2026, 3, 31)) == date(2027, 3, 31)


# --- the calendar reads the workflow, never a copy of it -----------------------


async def test_obligations_reflect_live_workflow_state(session_a, tenant_a):
    entity = await EntityService(session_a, tenant_a, PREPARER).create_entity(
        code="UK-01", name="Meridian UK Ltd", jurisdiction_code="UK"
    )
    workflow = WorkflowService(session_a, tenant_a, PREPARER)
    item = await workflow.create_work_item(
        entity_id=entity.id,
        period_key="2026-Q2",
        item_type="VAT_RETURN",
        title="VAT Q2",
    )
    await workflow.transition(item.id, WorkItemState.AWAITING_REVIEW)

    obligations = await CalendarService(session_a, tenant_a, PREPARER).obligations(
        entity_id=entity.id, year=2026, today=date(2026, 7, 23)
    )
    by_key = {(o.tax_type, o.period_key): o for o in obligations}

    # Five obligations for the year: four VAT quarters and the CT year.
    assert len(obligations) == 5
    q2 = by_key[("VAT", "2026-Q2")]
    assert q2.status == ObligationStatus.AWAITING_REVIEW
    assert q2.work_item_id == item.id
    assert by_key[("VAT", "2026-Q3")].status == ObligationStatus.NOT_STARTED
    assert by_key[("CT", "2026")].status == ObligationStatus.NOT_STARTED
    # Ordered by due date, soonest first.
    assert [o.due_date for o in obligations] == sorted(o.due_date for o in obligations)


async def test_overdue_means_past_deadline_without_an_approval(session_a, tenant_a):
    """Q1 2026 was due 7 May; on 23 July with nothing filed it is overdue. Approving an
    obligation clears the flag — approved late is late, but no longer outstanding."""
    entity = await EntityService(session_a, tenant_a, PREPARER).create_entity(
        code="UK-02", name="Meridian UK Ltd", jurisdiction_code="UK"
    )
    workflow = WorkflowService(session_a, tenant_a, PREPARER)
    item = await workflow.create_work_item(
        entity_id=entity.id, period_key="2026-Q1", item_type="VAT_RETURN", title="VAT Q1"
    )
    item = await workflow.transition(item.id, WorkItemState.AWAITING_REVIEW)

    service = CalendarService(session_a, tenant_a, PREPARER)
    today = date(2026, 7, 23)
    before = {
        o.period_key: o
        for o in await service.obligations(entity_id=entity.id, year=2026, today=today)
    }
    assert before["2026-Q1"].overdue is True  # past 7 May, not approved
    assert before["2026-Q2"].overdue is False  # due 7 Aug, still in the future

    await WorkflowService(session_a, tenant_a, REVIEWER).approve(
        item.id, content_hash=item.content_hash
    )
    after = {
        o.period_key: o
        for o in await service.obligations(entity_id=entity.id, year=2026, today=today)
    }
    assert after["2026-Q1"].status == ObligationStatus.APPROVED
    assert after["2026-Q1"].overdue is False
