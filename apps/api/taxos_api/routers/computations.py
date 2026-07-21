"""Computation and lineage endpoints (US-301, US-202)."""

import uuid
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from taxos_contracts.compliance import (
    BoxOut,
    ComputationOut,
    ComputeRequest,
    LineageEntryOut,
    LineageOut,
)
from taxos_core.compliance.pack import PackError
from taxos_core.compliance.service import ComputationService, NoValidatedDataError

from taxos_api.deps import Principal, current_principal, db_session
from taxos_api.errors import NotFoundError, ValidationFailed

router = APIRouter(tags=["compliance"])

PrincipalDep = Annotated[Principal, Depends(current_principal)]
SessionDep = Annotated[AsyncSession, Depends(db_session)]


def _service(session: AsyncSession, principal: Principal) -> ComputationService:
    return ComputationService(session, principal.tenant_id, principal.actor)


async def _to_out(service: ComputationService, computation) -> ComputationOut:  # noqa: ANN001
    lines = await service.get_lines(computation.id)
    return ComputationOut(
        id=computation.id,
        entity_id=computation.entity_id,
        period_key=computation.period_key,
        tax_type=computation.tax_type,
        pack_ref=computation.pack_ref,
        engine_version=computation.engine_version,
        inputs_hash=computation.inputs_hash,
        result_hash=computation.result_hash,
        unmapped_codes=computation.unmapped_codes,
        boxes=[
            BoxOut(
                box_id=line.box_id, label=line.label, value=str(line.value), derived=line.derived
            )
            for line in lines
        ],
        computed_at=computation.computed_at,
    )


@router.post("/computations", response_model=ComputationOut, status_code=status.HTTP_201_CREATED)
async def run_computation(
    body: ComputeRequest, principal: PrincipalDep, session: SessionDep
) -> ComputationOut:
    service = _service(session, principal)
    try:
        computation = await service.compute_vat(
            entity_id=body.entity_id,
            period_key=body.period_key,
            pack_version=body.pack_version,
        )
    except NoValidatedDataError as exc:
        raise ValidationFailed(str(exc)) from exc
    except PackError as exc:
        raise ValidationFailed(f"Rule pack error: {exc}") from exc
    return await _to_out(service, computation)


@router.get("/computations/{computation_id}", response_model=ComputationOut)
async def get_computation(
    computation_id: uuid.UUID, principal: PrincipalDep, session: SessionDep
) -> ComputationOut:
    service = _service(session, principal)
    computation = await service.get_computation(computation_id)
    if computation is None:
        raise NotFoundError(f"Computation {computation_id} not found")
    return await _to_out(service, computation)


@router.get("/computations/{computation_id}/boxes/{box_id}/lineage", response_model=LineageOut)
async def get_lineage(
    computation_id: uuid.UUID, box_id: str, principal: PrincipalDep, session: SessionDep
) -> LineageOut:
    """The drill-down behind any figure (US-202). The response includes the
    reconciliation total so a client can verify the sum without re-adding it."""
    service = _service(session, principal)
    computation = await service.get_computation(computation_id)
    if computation is None:
        raise NotFoundError(f"Computation {computation_id} not found")
    if box_id not in computation.result:
        raise NotFoundError(f"Box {box_id} is not part of this computation")

    entries = await service.get_lineage(computation_id, box_id)
    total = sum((entry.amount for entry in entries), Decimal("0"))
    return LineageOut(
        computation_id=computation_id,
        box_id=box_id,
        box_value=computation.result[box_id],
        contribution_total=str(total.quantize(Decimal("0.01"))),
        entries=[
            LineageEntryOut(
                row_id=entry.row_id,
                document_ref=entry.document_ref,
                counterparty=entry.counterparty,
                kind=entry.kind,
                amount=str(entry.amount),
                vat_code=entry.vat_code,
                citation_ref=entry.citation_ref,
            )
            for entry in entries
        ],
    )
