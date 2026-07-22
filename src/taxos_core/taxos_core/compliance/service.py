"""Compliance use-cases: run the engine, persist the snapshot, expose lineage.

The service does the I/O the engine refuses to: it materialises inputs, calls the pure
function, and stores the result with its lineage — all inside one audited transaction.
"""

import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taxos_core.compliance.engine import (
    EngineTransaction,
    compute_return,
    inputs_hash,
)
from taxos_core.compliance.models import Computation, ComputationLine, ComputationLineSource
from taxos_core.compliance.pack import RulePack, load_pack
from taxos_core.ingestion.models import Batch, BatchStatus, TransactionRow
from taxos_core.shared.persistence.uow import Actor, AuditedUnitOfWork

# Which source types are sales vs purchases. Direction is data about the feed, not a
# guess about the transaction. Corporation Tax has a single input stream ("CT"), which
# falls through to the pack's primary mapping slot.
_DIRECTION_BY_SOURCE = {"AP": "AP", "AR": "AR", "GL": "AP", "CT": "AP"}

# The feeds that belong to each tax type, so a return never sweeps in another tax's rows:
# a VAT computation must not read the Corporation Tax adjustment batch, or vice versa.
_VAT_SOURCES = frozenset({"AP", "AR", "GL"})
_CT_SOURCES = frozenset({"CT"})


class NoValidatedDataError(Exception):
    """No validated rows for this entity-period. The engine is not run on nothing —
    an empty return would look identical to an unfiled one."""


@dataclass
class LineageEntry:
    row_id: uuid.UUID
    document_ref: str
    counterparty: str
    kind: str
    amount: Decimal
    vat_code: str
    citation_ref: str


class ComputationService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID, actor: Actor) -> None:
        self._s = session
        self._tenant_id = tenant_id
        self._actor = actor

    async def compute_vat(
        self,
        *,
        entity_id: uuid.UUID,
        period_key: str,
        pack_name: str = "uk-vat",
        pack_version: str = "1.0.0",
        pack: RulePack | None = None,
    ) -> Computation:
        """Compute a UK VAT return from the validated sales/purchase batches."""
        pack = pack or load_pack(pack_name, pack_version)
        return await self._compute(
            entity_id=entity_id, period_key=period_key, pack=pack, source_types=_VAT_SOURCES
        )

    async def compute_corporation_tax(
        self,
        *,
        entity_id: uuid.UUID,
        period_key: str,
        pack_name: str = "uk-corporation-tax",
        pack_version: str = "1.0.0",
        pack: RulePack | None = None,
    ) -> Computation:
        """Compute a UK Corporation Tax charge from the adjustment batch.

        Same engine, same persistence, same audit and lineage as VAT — the only difference
        is the pack and which feed it reads. That is the whole point (AP-3)."""
        pack = pack or load_pack(pack_name, pack_version)
        return await self._compute(
            entity_id=entity_id, period_key=period_key, pack=pack, source_types=_CT_SOURCES
        )

    async def _compute(
        self,
        *,
        entity_id: uuid.UUID,
        period_key: str,
        pack: RulePack,
        source_types: frozenset[str],
    ) -> Computation:
        batches = (
            (
                await self._s.execute(
                    select(Batch).where(
                        Batch.entity_id == entity_id,
                        Batch.period_key == period_key,
                        Batch.source_type.in_(source_types),
                        Batch.status.in_(
                            [BatchStatus.VALIDATED, BatchStatus.VALIDATED_WITH_EXCEPTIONS]
                        ),
                    )
                )
            )
            .scalars()
            .all()
        )
        if not batches:
            raise NoValidatedDataError(
                f"No validated {pack.tax_type} data for entity {entity_id} period {period_key}"
            )

        direction_by_batch = {b.id: _DIRECTION_BY_SOURCE.get(b.source_type, "AP") for b in batches}
        rows = (
            (
                await self._s.execute(
                    select(TransactionRow).where(
                        TransactionRow.batch_id.in_(list(direction_by_batch))
                    )
                )
            )
            .scalars()
            .all()
        )

        engine_txns = [
            EngineTransaction(
                row_id=str(r.id),
                direction=direction_by_batch[r.batch_id],  # type: ignore[arg-type]
                vat_code=r.vat_code,
                net_amount=r.net_amount,
                vat_amount=r.vat_amount,
            )
            for r in rows
        ]

        result = compute_return(engine_txns, pack)
        in_hash = inputs_hash(engine_txns, pack)

        # Idempotence: the same inputs under the same pack return the existing snapshot
        # rather than creating a second one (the unique constraint backs this up).
        existing = (
            await self._s.execute(
                select(Computation).where(
                    Computation.inputs_hash == in_hash, Computation.pack_ref == pack.ref
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing

        uow = AuditedUnitOfWork(self._s, self._tenant_id, self._actor)
        computation = Computation(
            tenant_id=self._tenant_id,
            entity_id=entity_id,
            period_key=period_key,
            tax_type=pack.tax_type,
            pack_ref=pack.ref,
            pack_content_hash=pack.content_hash,
            engine_version=result.engine_version,
            inputs_hash=in_hash,
            result_hash=result.result_hash,
            result={box_id: str(bv.value) for box_id, bv in result.boxes.items()},
            batch_ids=[str(b.id) for b in batches],
            unmapped_codes=result.unmapped_codes,
            created_by=self._actor.ref,
        )
        self._s.add(computation)
        await self._s.flush()

        for box_id, box_value in result.boxes.items():
            line = ComputationLine(
                tenant_id=self._tenant_id,
                computation_id=computation.id,
                box_id=box_id,
                label=box_value.label,
                value=box_value.value,
                derived=box_value.derived,
            )
            self._s.add(line)
            await self._s.flush()

            for contribution in result.contributions_for(box_id):
                self._s.add(
                    ComputationLineSource(
                        tenant_id=self._tenant_id,
                        line_id=line.id,
                        row_id=uuid.UUID(contribution.row_id),
                        kind=contribution.kind,
                        amount=contribution.amount,
                        vat_code=contribution.vat_code,
                        citation_ref=contribution.citation_ref,
                    )
                )

        uow.record(
            "computation.completed",
            "computation",
            str(computation.id),
            after={
                "entity_id": str(entity_id),
                "period": period_key,
                "pack": pack.ref,
                "engine": result.engine_version,
                "inputs_hash": in_hash,
                "result_hash": result.result_hash,
                "boxes": computation.result,
            },
        )
        uow.publish(
            "ComputationCompleted",
            {
                "computation_id": str(computation.id),
                "entity_id": str(entity_id),
                "period_key": period_key,
                "pack_ref": pack.ref,
                "result_hash": result.result_hash,
            },
        )
        await uow.commit()
        return computation

    async def get_computation(self, computation_id: uuid.UUID) -> Computation | None:
        return (
            await self._s.execute(select(Computation).where(Computation.id == computation_id))
        ).scalar_one_or_none()

    async def get_lines(self, computation_id: uuid.UUID) -> list[ComputationLine]:
        result = await self._s.execute(
            select(ComputationLine)
            .where(ComputationLine.computation_id == computation_id)
            .order_by(ComputationLine.box_id)
        )
        return list(result.scalars().all())

    async def get_lineage(self, computation_id: uuid.UUID, box_id: str) -> list[LineageEntry]:
        """US-202: drill from a box to the transactions that produced it."""
        stmt = (
            select(ComputationLineSource, TransactionRow)
            .join(ComputationLine, ComputationLine.id == ComputationLineSource.line_id)
            .join(TransactionRow, TransactionRow.id == ComputationLineSource.row_id)
            .where(
                ComputationLine.computation_id == computation_id,
                ComputationLine.box_id == box_id,
            )
            .order_by(TransactionRow.document_ref)
        )
        return [
            LineageEntry(
                row_id=row.id,
                document_ref=row.document_ref,
                counterparty=row.counterparty,
                kind=source.kind,
                amount=source.amount,
                vat_code=source.vat_code,
                citation_ref=source.citation_ref,
            )
            for source, row in (await self._s.execute(stmt)).all()
        ]
