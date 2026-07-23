"""Filing calendar endpoints (US-501)."""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from taxos_core.reporting.calendar import CalendarService

from taxos_api.deps import Principal, current_principal, db_session

router = APIRouter(tags=["calendar"])

PrincipalDep = Annotated[Principal, Depends(current_principal)]
SessionDep = Annotated[AsyncSession, Depends(db_session)]


class ObligationOut(BaseModel):
    tax_type: str
    period_key: str
    period_label: str
    period_end: date
    due_date: date
    basis: str
    status: str
    overdue: bool
    work_item_id: uuid.UUID | None


@router.get("/calendar/obligations", response_model=list[ObligationOut])
async def list_obligations(
    principal: PrincipalDep,
    session: SessionDep,
    entity_id: uuid.UUID,
    year: int = 2026,
) -> list[ObligationOut]:
    """The year's filing obligations with statutory deadlines and live workflow status.
    Derived, never stored — the calendar cannot disagree with the workflow."""
    service = CalendarService(session, principal.tenant_id, principal.actor)
    obligations = await service.obligations(entity_id=entity_id, year=year, today=date.today())
    return [
        ObligationOut(
            tax_type=o.tax_type,
            period_key=o.period_key,
            period_label=o.period_label,
            period_end=o.period_end,
            due_date=o.due_date,
            basis=o.basis,
            status=o.status,
            overdue=o.overdue,
            work_item_id=o.work_item_id,
        )
        for o in obligations
    ]
