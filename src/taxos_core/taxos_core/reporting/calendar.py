"""The filing calendar: every obligation, its statutory deadline, where it stands (US-501).

Obligations are DERIVED, not stored. The entity's registrations imply what must be filed
(UK VAT quarterly, Corporation Tax annually), the period implies the statutory deadline, and
the live workflow state says how far each filing has progressed. A calendar row is therefore
always true — there is no separate obligations table to fall out of date, and "the calendar
says approved" and "the approval exists" cannot disagree because they are the same fact.

Deadlines carry their statutory basis, the same discipline as every other figure here:
a date a reviewer cannot trace to a rule is as useless as a number they cannot.
"""

import uuid
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taxos_core.compliance.models import Computation
from taxos_core.ingestion.service import period_bounds
from taxos_core.workflow.models import WorkItem
from taxos_core.workflow.states import WorkItemState


class ObligationStatus:
    NOT_STARTED = "NOT_STARTED"
    IN_PREPARATION = "IN_PREPARATION"
    AWAITING_REVIEW = "AWAITING_REVIEW"
    APPROVED = "APPROVED"


# Work-item state → calendar status. CHANGES_REQUESTED is back in preparation by definition;
# CANCELLED means the filing still has to happen, so the obligation reads not-started.
_STATUS_BY_STATE = {
    WorkItemState.DRAFT: ObligationStatus.IN_PREPARATION,
    WorkItemState.AWAITING_REVIEW: ObligationStatus.AWAITING_REVIEW,
    WorkItemState.CHANGES_REQUESTED: ObligationStatus.IN_PREPARATION,
    WorkItemState.APPROVED: ObligationStatus.APPROVED,
    WorkItemState.CANCELLED: ObligationStatus.NOT_STARTED,
}

_ITEM_TYPE_TO_TAX = {"VAT_RETURN": "VAT", "CT_COMPUTATION": "CT"}


@dataclass(frozen=True)
class FilingObligation:
    tax_type: str
    period_key: str
    period_label: str
    period_end: date
    due_date: date
    basis: str  # the statutory rule the deadline comes from
    status: str
    overdue: bool
    work_item_id: uuid.UUID | None


def _month_end(year: int, month: int) -> date:
    if month == 12:
        return date(year, 12, 31)
    return date(year, month + 1, 1) - timedelta(days=1)


def vat_due_date(period_key: str) -> date:
    """MTD VAT: one calendar month and seven days after the end of the period
    (VAT Notice 700/12 §5). VAT periods end at a month end, so "one calendar month after"
    is the end of the following month — 30 June → 31 July → 7 August."""
    _, period_end = period_bounds(period_key)
    next_month = period_end.month % 12 + 1
    next_year = period_end.year + (1 if period_end.month == 12 else 0)
    return _month_end(next_year, next_month) + timedelta(days=7)


def ct_period_end(period_key: str) -> date:
    """CT period "2026" is the accounting year ended 31 March 2026 — Meridian's year end,
    matching the seeded computation. A real system reads this off the entity's accounting
    reference date; the convention is the demo's simplification, documented here."""
    return date(int(period_key), 3, 31)


def ct_filing_due_date(period_end: date) -> date:
    """CT600 filing: twelve months after the end of the accounting period
    (FA 1998 Sch.18 para.14)."""
    try:
        return period_end.replace(year=period_end.year + 1)
    except ValueError:  # 29 Feb
        return date(period_end.year + 1, 2, 28)


class CalendarService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID, actor) -> None:  # noqa: ANN001
        self._s = session
        self._tenant_id = tenant_id
        self._actor = actor

    async def obligations(
        self, *, entity_id: uuid.UUID, year: int, today: date
    ) -> list[FilingObligation]:
        """The year's obligations for an entity, joined to live workflow state, ordered by
        due date. Overdue = past the statutory deadline without an approval."""
        expected: list[tuple[str, str]] = [("VAT", f"{year}-Q{q}") for q in (1, 2, 3, 4)]
        expected.append(("CT", str(year)))

        items = (
            (await self._s.execute(select(WorkItem).where(WorkItem.entity_id == entity_id)))
            .scalars()
            .all()
        )
        # Most-advanced-wins if several items exist for one obligation: an approval anywhere
        # means the filing position is approved.
        rank = {
            ObligationStatus.NOT_STARTED: 0,
            ObligationStatus.IN_PREPARATION: 1,
            ObligationStatus.AWAITING_REVIEW: 2,
            ObligationStatus.APPROVED: 3,
        }
        item_by_key: dict[tuple[str, str], WorkItem] = {}
        for item in items:
            tax_type = _ITEM_TYPE_TO_TAX.get(item.item_type)
            if tax_type is None:
                continue
            key = (tax_type, item.period_key)
            current = item_by_key.get(key)
            if (
                current is None
                or rank[_STATUS_BY_STATE[item.state]] > rank[_STATUS_BY_STATE[current.state]]
            ):
                item_by_key[key] = item

        computed = {
            (c.tax_type, c.period_key)
            for c in (
                await self._s.execute(select(Computation).where(Computation.entity_id == entity_id))
            )
            .scalars()
            .all()
        }

        obligations: list[FilingObligation] = []
        for tax_type, period_key in expected:
            if tax_type == "VAT":
                _, period_end = period_bounds(period_key)
                due = vat_due_date(period_key)
                label = f"VAT return · {period_key}"
                basis = "VAT Notice 700/12 §5 — one month and seven days after the period end"
            else:
                period_end = ct_period_end(period_key)
                due = ct_filing_due_date(period_end)
                label = f"Corporation Tax · FY{period_key}"
                basis = "FA 1998 Sch.18 para.14 — twelve months after the accounting period end"

            item = item_by_key.get((tax_type, period_key))
            if item is not None:
                status = _STATUS_BY_STATE[item.state]
            elif (tax_type, period_key) in computed:
                status = ObligationStatus.IN_PREPARATION
            else:
                status = ObligationStatus.NOT_STARTED

            obligations.append(
                FilingObligation(
                    tax_type=tax_type,
                    period_key=period_key,
                    period_label=label,
                    period_end=period_end,
                    due_date=due,
                    basis=basis,
                    status=status,
                    overdue=today > due and status != ObligationStatus.APPROVED,
                    work_item_id=item.id if item is not None else None,
                )
            )

        obligations.sort(key=lambda o: o.due_date)
        return obligations
