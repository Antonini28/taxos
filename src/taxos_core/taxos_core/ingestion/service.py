"""Ingestion use-cases (US-201).

One service call = one UoW = one atomic, audited action — the pattern established in
masterdata, applied to the first real data path.
"""

import csv
import hashlib
import io
import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from taxos_core.ingestion.models import (
    Batch,
    BatchStatus,
    QuarantineRow,
    TransactionRow,
    ValidationResult,
)
from taxos_core.ingestion.rules import RULESET_VERSION, validate_row
from taxos_core.shared.persistence.base import utcnow
from taxos_core.shared.persistence.uow import Actor, AuditedUnitOfWork


class DuplicateBatchError(Exception):
    """Same content already ingested for this period (US-201). Carries the original."""

    def __init__(self, original_batch_id: uuid.UUID) -> None:
        super().__init__(f"Identical content already ingested as batch {original_batch_id}")
        self.original_batch_id = original_batch_id


@dataclass
class ValidationReport:
    batch_id: uuid.UUID
    status: str
    row_count: int
    accepted_count: int
    quarantined_count: int
    control_total: Decimal
    rule_breakdown: dict[str, int]


def period_bounds(period_key: str) -> tuple[date, date]:
    """ "2026-Q2" → (2026-04-01, 2026-06-30). Period semantics are explicit, never inferred."""
    year_str, quarter_str = period_key.split("-Q")
    year, quarter = int(year_str), int(quarter_str)
    start_month = 3 * (quarter - 1) + 1
    start = date(year, start_month, 1)
    end_month = start_month + 2
    last_day = 31 if end_month in (1, 3, 5, 7, 8, 10, 12) else 30
    if end_month == 2:
        last_day = 29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28
    return start, date(year, end_month, last_day)


class IngestionService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID, actor: Actor) -> None:
        self._s = session
        self._tenant_id = tenant_id
        self._actor = actor

    async def ingest_csv(
        self,
        *,
        entity_id: uuid.UUID,
        period_key: str,
        source_type: str,
        filename: str,
        content: bytes,
    ) -> ValidationReport:
        content_hash = hashlib.sha256(content).hexdigest()
        await self._reject_if_duplicate(content_hash, period_key)

        period_start, period_end = period_bounds(period_key)
        rows = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))

        uow = AuditedUnitOfWork(self._s, self._tenant_id, self._actor)
        batch = Batch(
            tenant_id=self._tenant_id,
            entity_id=entity_id,
            period_key=period_key,
            source_type=source_type,
            filename=filename,
            content_hash=content_hash,
            status=BatchStatus.VALIDATING,
            row_count=len(rows),
            created_by=self._actor.ref,
        )
        self._s.add(batch)
        await self._s.flush()

        accepted, quarantined, rule_counts, control_total = await self._validate_rows(
            batch.id, rows, period_start, period_end
        )

        batch.accepted_count = accepted
        batch.quarantined_count = quarantined
        batch.control_total = control_total
        batch.status = (
            BatchStatus.VALIDATED_WITH_EXCEPTIONS if quarantined else BatchStatus.VALIDATED
        )
        batch.validated_at = utcnow()

        uow.record(
            "batch.ingested",
            "batch",
            str(batch.id),
            after={
                "filename": filename,
                "period": period_key,
                "rows": len(rows),
                "accepted": accepted,
                "quarantined": quarantined,
                "status": batch.status,
                "ruleset_version": RULESET_VERSION,
            },
        )
        uow.publish(
            "BatchValidated",
            {
                "batch_id": str(batch.id),
                "entity_id": str(entity_id),
                "period_key": period_key,
                "accepted": accepted,
                "quarantined": quarantined,
            },
        )
        if quarantined:
            uow.publish(
                "RowsQuarantined",
                {"batch_id": str(batch.id), "count": quarantined, "rules": rule_counts},
            )
        await uow.commit()

        return ValidationReport(
            batch_id=batch.id,
            status=batch.status,
            row_count=len(rows),
            accepted_count=accepted,
            quarantined_count=quarantined,
            control_total=control_total,
            rule_breakdown=rule_counts,
        )

    async def _reject_if_duplicate(self, content_hash: str, period_key: str) -> None:
        existing = await self._s.execute(
            select(Batch.id).where(
                Batch.content_hash == content_hash, Batch.period_key == period_key
            )
        )
        original = existing.scalar_one_or_none()
        if original is not None:
            raise DuplicateBatchError(original)

    async def _validate_rows(
        self,
        batch_id: uuid.UUID,
        rows: list[dict[str, Any]],
        period_start: date,
        period_end: date,
    ) -> tuple[int, int, dict[str, int], Decimal]:
        accepted = quarantined = 0
        rule_counts: dict[str, int] = {}
        rule_samples: dict[str, list[int]] = {}
        control_total = Decimal("0")

        for index, raw in enumerate(rows, start=1):
            parsed, failures = validate_row(raw, period_start=period_start, period_end=period_end)
            if parsed is None or failures:
                quarantined += 1
                for failure in failures:
                    rule_counts[failure.rule] = rule_counts.get(failure.rule, 0) + 1
                    rule_samples.setdefault(failure.rule, [])
                    if len(rule_samples[failure.rule]) < 5:
                        rule_samples[failure.rule].append(index)
                self._s.add(
                    QuarantineRow(
                        tenant_id=self._tenant_id,
                        batch_id=batch_id,
                        row_number=index,
                        source_payload=raw,
                        failures=[
                            {"rule": f.rule, "message": f.message, "field": f.field}
                            for f in failures
                        ],
                    )
                )
                continue

            accepted += 1
            control_total += parsed.net_amount + parsed.vat_amount
            row_hash = hashlib.sha256(
                f"{parsed.document_ref}|{parsed.document_date}|{parsed.net_amount}|"
                f"{parsed.vat_amount}|{parsed.vat_code}".encode()
            ).hexdigest()
            self._s.add(
                TransactionRow(
                    tenant_id=self._tenant_id,
                    batch_id=batch_id,
                    row_number=index,
                    row_hash=row_hash,
                    document_ref=parsed.document_ref,
                    document_date=parsed.document_date,
                    counterparty=parsed.counterparty,
                    net_amount=parsed.net_amount,
                    vat_amount=parsed.vat_amount,
                    vat_code=parsed.vat_code,
                    currency=parsed.currency,
                    source_payload=raw,
                )
            )

        for rule_id, count in rule_counts.items():
            self._s.add(
                ValidationResult(
                    tenant_id=self._tenant_id,
                    batch_id=batch_id,
                    rule_id=rule_id,
                    severity="ERROR",
                    failed_count=count,
                    sample_rows=rule_samples.get(rule_id, []),
                )
            )

        return accepted, quarantined, rule_counts, control_total

    async def get_validation_report(self, batch_id: uuid.UUID) -> ValidationReport | None:
        batch = (
            await self._s.execute(select(Batch).where(Batch.id == batch_id))
        ).scalar_one_or_none()
        if batch is None:
            return None
        results = (
            (
                await self._s.execute(
                    select(ValidationResult).where(ValidationResult.batch_id == batch_id)
                )
            )
            .scalars()
            .all()
        )
        return ValidationReport(
            batch_id=batch.id,
            status=batch.status,
            row_count=batch.row_count,
            accepted_count=batch.accepted_count,
            quarantined_count=batch.quarantined_count,
            control_total=batch.control_total or Decimal("0"),
            rule_breakdown={r.rule_id: r.failed_count for r in results},
        )

    async def list_quarantine(self, batch_id: uuid.UUID) -> list[QuarantineRow]:
        result = await self._s.execute(
            select(QuarantineRow)
            .where(QuarantineRow.batch_id == batch_id)
            .order_by(QuarantineRow.row_number)
        )
        return list(result.scalars().all())

    async def count_validated_rows(self, batch_id: uuid.UUID) -> int:
        result = await self._s.execute(
            select(func.count())
            .select_from(TransactionRow)
            .where(TransactionRow.batch_id == batch_id)
        )
        return int(result.scalar_one())
