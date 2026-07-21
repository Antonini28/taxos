"""Ingestion endpoints (US-201).

Routers translate; services decide. Every handler here is parse → call service →
shape response, with domain errors raised by the service and rendered by the boundary.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from taxos_contracts.ingestion import (
    BatchAccepted,
    BatchOut,
    QuarantinedRow,
    ValidationReportOut,
)
from taxos_core.ingestion.models import Batch
from taxos_core.ingestion.service import DuplicateBatchError, IngestionService

from taxos_api.deps import Principal, current_principal, db_session
from taxos_api.errors import DuplicateContentError, NotFoundError, ValidationFailed

router = APIRouter(prefix="/batches", tags=["ingestion"])

MAX_UPLOAD_BYTES = 500 * 1024 * 1024  # matches the documented per-file cap

PrincipalDep = Annotated[Principal, Depends(current_principal)]
SessionDep = Annotated[AsyncSession, Depends(db_session)]


@router.post("", response_model=BatchAccepted, status_code=status.HTTP_202_ACCEPTED)
async def upload_batch(
    principal: PrincipalDep,
    session: SessionDep,
    entity_id: Annotated[uuid.UUID, Form()],
    period_key: Annotated[str, Form()],
    source_type: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
) -> BatchAccepted:
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValidationFailed(f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)}MB limit")
    if not content:
        raise ValidationFailed("File is empty")

    service = IngestionService(session, principal.tenant_id, principal.actor)
    try:
        report = await service.ingest_csv(
            entity_id=entity_id,
            period_key=period_key,
            source_type=source_type,
            filename=file.filename or "upload.csv",
            content=content,
        )
    except DuplicateBatchError as exc:
        # 409 naming the original — "rejected with reference to the original batch" (US-201)
        raise DuplicateContentError(
            f"Identical content already ingested for {period_key} as batch {exc.original_batch_id}"
        ) from exc

    return BatchAccepted(
        batch_id=report.batch_id, status=report.status, filename=file.filename or "upload.csv"
    )


@router.get("/{batch_id}/validation-report", response_model=ValidationReportOut)
async def get_validation_report(
    batch_id: uuid.UUID, principal: PrincipalDep, session: SessionDep
) -> ValidationReportOut:
    service = IngestionService(session, principal.tenant_id, principal.actor)
    report = await service.get_validation_report(batch_id)
    if report is None:
        raise NotFoundError(f"Batch {batch_id} not found")
    return ValidationReportOut(
        batch_id=report.batch_id,
        status=report.status,
        row_count=report.row_count,
        accepted_count=report.accepted_count,
        quarantined_count=report.quarantined_count,
        control_total=str(report.control_total),
        rule_breakdown=report.rule_breakdown,
    )


@router.get("/{batch_id}/quarantine", response_model=list[QuarantinedRow])
async def list_quarantine(
    batch_id: uuid.UUID, principal: PrincipalDep, session: SessionDep
) -> list[QuarantinedRow]:
    service = IngestionService(session, principal.tenant_id, principal.actor)
    rows = await service.list_quarantine(batch_id)
    return [
        QuarantinedRow(
            row_number=r.row_number, failures=r.failures, source_payload=r.source_payload
        )
        for r in rows
    ]


@router.get("", response_model=list[BatchOut])
async def list_batches(principal: PrincipalDep, session: SessionDep) -> list[BatchOut]:
    result = await session.execute(select(Batch).order_by(Batch.created_at.desc()).limit(50))
    return [BatchOut.model_validate(b, from_attributes=True) for b in result.scalars().all()]
