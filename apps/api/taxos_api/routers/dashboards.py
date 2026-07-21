"""Dashboard endpoints (FR-601). Read-only aggregates for the executive view."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from taxos_core.reporting.service import ReportingService

from taxos_api.deps import Principal, current_principal, db_session

router = APIRouter(prefix="/dashboards", tags=["reporting"])

PrincipalDep = Annotated[Principal, Depends(current_principal)]
SessionDep = Annotated[AsyncSession, Depends(db_session)]


class DataQualityOut(BaseModel):
    total_rows: int
    accepted_rows: int
    quarantined_rows: int
    quarantine_rate: float
    batches: int


class PeriodLiabilityOut(BaseModel):
    period_key: str
    output_vat: str
    input_vat: str
    net_due: str


class VatCodeBreakdownOut(BaseModel):
    vat_code: str
    net_amount: str
    transaction_count: int


class ComplianceCellOut(BaseModel):
    entity_code: str
    entity_name: str
    period_key: str
    state: str
    net_due: str | None


class ExecutiveDashboardOut(BaseModel):
    as_of: str
    entities: int
    net_vat_due: str
    open_items: int
    approved_items: int
    data_quality: DataQualityOut
    liability_trend: list[PeriodLiabilityOut]
    code_breakdown: list[VatCodeBreakdownOut]
    compliance: list[ComplianceCellOut]


@router.get("/executive", response_model=ExecutiveDashboardOut)
async def executive_dashboard(
    principal: PrincipalDep, session: SessionDep
) -> ExecutiveDashboardOut:
    dashboard = await ReportingService(session, principal.tenant_id).executive_dashboard()
    return ExecutiveDashboardOut(
        as_of=dashboard.as_of.isoformat(),
        entities=dashboard.entities,
        net_vat_due=dashboard.net_vat_due,
        open_items=dashboard.open_items,
        approved_items=dashboard.approved_items,
        data_quality=DataQualityOut(**dashboard.data_quality.__dict__),
        liability_trend=[PeriodLiabilityOut(**p.__dict__) for p in dashboard.liability_trend],
        code_breakdown=[VatCodeBreakdownOut(**c.__dict__) for c in dashboard.code_breakdown],
        compliance=[ComplianceCellOut(**c.__dict__) for c in dashboard.compliance],
    )
