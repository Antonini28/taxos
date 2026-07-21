"""Dashboard read models (FR-601).

Read-only by construction: this service holds no UoW and writes nothing. Every figure it
returns carries enough context to be drilled into — a KPI that cannot be traced is a
rumour, and the executive dashboard is where rumours do the most damage.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from taxos_core.compliance.models import Computation
from taxos_core.ingestion.models import Batch, TransactionRow
from taxos_core.masterdata.models import LegalEntity
from taxos_core.workflow.models import Approval, WorkItem
from taxos_core.workflow.states import WorkItemState


@dataclass
class PeriodLiability:
    period_key: str
    output_vat: str
    input_vat: str
    net_due: str


@dataclass
class VatCodeBreakdown:
    vat_code: str
    net_amount: str
    transaction_count: int


@dataclass
class DataQuality:
    total_rows: int
    accepted_rows: int
    quarantined_rows: int
    quarantine_rate: float
    batches: int


@dataclass
class ComplianceCell:
    entity_code: str
    entity_name: str
    period_key: str
    state: str
    net_due: str | None


@dataclass
class ExecutiveDashboard:
    as_of: datetime
    entities: int
    net_vat_due: str
    open_items: int
    approved_items: int
    data_quality: DataQuality
    liability_trend: list[PeriodLiability] = field(default_factory=list)
    code_breakdown: list[VatCodeBreakdown] = field(default_factory=list)
    compliance: list[ComplianceCell] = field(default_factory=list)


class ReportingService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._s = session
        self._tenant_id = tenant_id

    async def executive_dashboard(self) -> ExecutiveDashboard:
        entities = list((await self._s.execute(select(LegalEntity))).scalars().all())
        entity_by_id = {e.id: e for e in entities}

        computations = list(
            (
                await self._s.execute(
                    select(Computation).order_by(Computation.period_key, Computation.computed_at)
                )
            )
            .scalars()
            .all()
        )

        # Keep the latest computation per (entity, period): superseded snapshots stay in
        # the record for audit, but a dashboard should show the current position.
        latest: dict[tuple[uuid.UUID, str], Computation] = {}
        for computation in computations:
            latest[(computation.entity_id, computation.period_key)] = computation

        liability_by_period: dict[str, tuple[Decimal, Decimal]] = {}
        net_due_total = Decimal("0")
        for computation in latest.values():
            output_vat = Decimal(computation.result.get("box_1", "0"))
            input_vat = Decimal(computation.result.get("box_4", "0"))
            accumulated = liability_by_period.get(
                computation.period_key, (Decimal("0"), Decimal("0"))
            )
            liability_by_period[computation.period_key] = (
                accumulated[0] + output_vat,
                accumulated[1] + input_vat,
            )
            net_due_total += Decimal(computation.result.get("box_5", "0"))

        work_items = list((await self._s.execute(select(WorkItem))).scalars().all())
        open_items = sum(
            1
            for item in work_items
            if item.state in (WorkItemState.DRAFT, WorkItemState.AWAITING_REVIEW)
        )
        approved_items = sum(1 for item in work_items if item.state == WorkItemState.APPROVED)

        batches = list((await self._s.execute(select(Batch))).scalars().all())
        total_rows = sum(b.row_count for b in batches)
        accepted_rows = sum(b.accepted_count for b in batches)
        quarantined_rows = sum(b.quarantined_count for b in batches)

        code_rows = (
            await self._s.execute(
                select(
                    TransactionRow.vat_code,
                    func.sum(TransactionRow.net_amount),
                    func.count(TransactionRow.id),
                ).group_by(TransactionRow.vat_code)
            )
        ).all()

        state_by_entity_period = {
            (item.entity_id, item.period_key): item.state for item in work_items
        }
        compliance: list[ComplianceCell] = []
        for (entity_id, period_key), computation in sorted(latest.items(), key=lambda kv: kv[0][1]):
            entity = entity_by_id.get(entity_id)
            if entity is None:
                continue
            compliance.append(
                ComplianceCell(
                    entity_code=entity.code,
                    entity_name=entity.name,
                    period_key=period_key,
                    state=state_by_entity_period.get((entity_id, period_key), "NOT_STARTED"),
                    net_due=computation.result.get("box_5"),
                )
            )

        return ExecutiveDashboard(
            as_of=datetime.now(UTC),
            entities=len(entities),
            net_vat_due=str(net_due_total.quantize(Decimal("0.01"))),
            open_items=open_items,
            approved_items=approved_items,
            data_quality=DataQuality(
                total_rows=total_rows,
                accepted_rows=accepted_rows,
                quarantined_rows=quarantined_rows,
                quarantine_rate=round(quarantined_rows / total_rows * 100, 1)
                if total_rows
                else 0.0,
                batches=len(batches),
            ),
            liability_trend=[
                PeriodLiability(
                    period_key=period,
                    output_vat=str(output),
                    input_vat=str(input_vat),
                    net_due=str(abs(output - input_vat)),
                )
                for period, (output, input_vat) in sorted(liability_by_period.items())
            ],
            code_breakdown=[
                VatCodeBreakdown(
                    vat_code=code,
                    net_amount=str(Decimal(net or 0).quantize(Decimal("0.01"))),
                    transaction_count=int(count),
                )
                for code, net, count in sorted(code_rows, key=lambda r: -(r[1] or 0))
            ],
            compliance=compliance,
        )

    async def recent_approvals(self, limit: int = 5) -> list[Approval]:
        result = await self._s.execute(
            select(Approval).order_by(Approval.granted_at.desc()).limit(limit)
        )
        return list(result.scalars().all())
