"""Risk use-cases: scan a population, disposition a flag.

Scanning is idempotent per (entity, period, detector version): re-scanning does not create
duplicate anomalies for rows already flagged, so the queue never doubles under a repeated
run. Disposition is the human act (ML-1) and the point at which a labelled example is
recorded — reason-coded, attributed, and timestamped.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taxos_core.ingestion.models import Batch, TransactionRow
from taxos_core.risk.detectors import DETECTOR_VERSION, Transaction, detect_all
from taxos_core.risk.models import (
    CONFIRM_REASONS,
    DISMISS_REASONS,
    Anomaly,
    AnomalyScan,
    AnomalyStatus,
)
from taxos_core.shared.persistence.base import utcnow
from taxos_core.shared.persistence.uow import Actor, AuditedUnitOfWork


class InvalidDispositionError(Exception):
    """A disposition reason that is not in the taxonomy. Reasons are the label space; an
    ad-hoc reason would be an unlabelled example masquerading as a labelled one."""


@dataclass
class ScanResult:
    scan_id: uuid.UUID
    rows_scanned: int
    flagged: int
    new_anomalies: int


class RiskService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID, actor: Actor) -> None:
        self._s = session
        self._tenant_id = tenant_id
        self._actor = actor

    async def scan(self, *, entity_id: uuid.UUID, period_key: str) -> ScanResult:
        rows = list(
            (
                await self._s.execute(
                    select(TransactionRow)
                    .join(Batch, Batch.id == TransactionRow.batch_id)
                    .where(Batch.entity_id == entity_id, Batch.period_key == period_key)
                )
            )
            .scalars()
            .all()
        )
        row_by_id = {str(r.id): r for r in rows}
        transactions = [
            Transaction(
                row_id=str(r.id),
                document_ref=r.document_ref,
                counterparty=r.counterparty,
                net_amount=r.net_amount,
                vat_amount=r.vat_amount,
                vat_code=r.vat_code,
            )
            for r in rows
        ]
        findings = detect_all(transactions)

        # Don't re-flag a (row, detector) already recorded — re-scanning is safe.
        existing = {
            (a.row_id, a.detector)
            for a in (
                await self._s.execute(
                    select(Anomaly).where(
                        Anomaly.entity_id == entity_id, Anomaly.period_key == period_key
                    )
                )
            )
            .scalars()
            .all()
        }

        uow = AuditedUnitOfWork(self._s, self._tenant_id, self._actor)
        scan = AnomalyScan(
            tenant_id=self._tenant_id,
            entity_id=entity_id,
            period_key=period_key,
            detector_version=DETECTOR_VERSION,
            rows_scanned=len(rows),
            flagged=len(findings),
            created_by=self._actor.ref,
        )
        self._s.add(scan)
        await self._s.flush()

        new_count = 0
        for finding in findings:
            if (uuid.UUID(finding.row_id), finding.detector) in existing:
                continue
            self._s.add(
                Anomaly(
                    tenant_id=self._tenant_id,
                    entity_id=entity_id,
                    period_key=period_key,
                    row_id=uuid.UUID(finding.row_id),
                    document_ref=finding.document_ref,
                    detector=finding.detector,
                    detector_version=DETECTOR_VERSION,
                    anomaly_type=finding.anomaly_type,
                    severity=finding.severity,
                    explanation=finding.explanation,
                    evidence=finding.evidence,
                    created_by=self._actor.ref,
                )
            )
            new_count += 1

        uow.record(
            "anomaly_scan.completed",
            "anomaly_scan",
            str(scan.id),
            after={
                "entity_id": str(entity_id),
                "period": period_key,
                "rows_scanned": len(rows),
                "flagged": len(findings),
                "new": new_count,
                "detector_version": DETECTOR_VERSION,
            },
        )
        uow.publish(
            "AnomalyScanCompleted",
            {"scan_id": str(scan.id), "entity_id": str(entity_id), "new_anomalies": new_count},
        )
        await uow.commit()

        _ = row_by_id  # retained for future SHAP-style enrichment
        return ScanResult(
            scan_id=scan.id,
            rows_scanned=len(rows),
            flagged=len(findings),
            new_anomalies=new_count,
        )

    async def disposition(
        self,
        anomaly_id: uuid.UUID,
        *,
        confirm: bool,
        reason: str,
        note: str | None = None,
    ) -> Anomaly:
        """Confirm or dismiss an anomaly with a reason code. This is the human act that
        turns a flag into a labelled example (FR-506)."""
        valid = CONFIRM_REASONS if confirm else DISMISS_REASONS
        if reason not in valid:
            raise InvalidDispositionError(
                f"'{reason}' is not a valid {'confirm' if confirm else 'dismiss'} reason. "
                f"Expected one of: {', '.join(valid)}"
            )

        anomaly = (
            await self._s.execute(select(Anomaly).where(Anomaly.id == anomaly_id))
        ).scalar_one()

        uow = AuditedUnitOfWork(self._s, self._tenant_id, self._actor)
        before_status = anomaly.status
        anomaly.status = AnomalyStatus.CONFIRMED if confirm else AnomalyStatus.DISMISSED
        anomaly.disposition_reason = reason
        anomaly.disposition_note = note
        anomaly.dispositioned_by = self._actor.ref
        anomaly.dispositioned_at = utcnow()

        uow.record(
            "anomaly.dispositioned",
            "anomaly",
            str(anomaly.id),
            before={"status": before_status},
            after={
                "status": anomaly.status,
                "reason": reason,
                "by": self._actor.ref,
            },
        )
        uow.publish(
            "AnomalyDispositioned",
            {"anomaly_id": str(anomaly.id), "status": anomaly.status, "reason": reason},
        )
        await uow.commit()
        return anomaly

    async def list_anomalies(
        self, *, status: str | None = None, entity_id: uuid.UUID | None = None
    ) -> list[Anomaly]:
        stmt = select(Anomaly).order_by(
            # Highest severity first, then most recent: the queue is ordered by what a
            # reviewer should look at first, not by insertion order.
            Anomaly.severity.asc(),  # HIGH < LOW alphabetically, so flip below
            Anomaly.created_at.desc(),
        )
        # Severity ordering: HIGH, MEDIUM, LOW — express explicitly rather than by accident.
        severity_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        if status:
            stmt = stmt.where(Anomaly.status == status)
        if entity_id:
            stmt = stmt.where(Anomaly.entity_id == entity_id)
        anomalies = list((await self._s.execute(stmt)).scalars().all())
        return sorted(anomalies, key=lambda a: (severity_rank.get(a.severity, 9), a.created_at))

    async def summary(self) -> dict[str, int]:
        anomalies = list((await self._s.execute(select(Anomaly))).scalars().all())
        return {
            "open": sum(1 for a in anomalies if a.status == AnomalyStatus.OPEN),
            "confirmed": sum(1 for a in anomalies if a.status == AnomalyStatus.CONFIRMED),
            "dismissed": sum(1 for a in anomalies if a.status == AnomalyStatus.DISMISSED),
            "high_open": sum(
                1 for a in anomalies if a.status == AnomalyStatus.OPEN and a.severity == "HIGH"
            ),
        }
