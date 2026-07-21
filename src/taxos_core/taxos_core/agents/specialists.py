"""Specialist agents.

Each takes a TaskEnvelope and returns a ResultEnvelope. What varies between "stub mode"
and a live model is only the *narrative* an agent writes — the figures always come from
the deterministic engine, and the governance is identical either way (AP-2).

That is the point worth noticing: the parts of an agent that could be wrong are the parts
that never touch a number.
"""

import time
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taxos_core.agents.envelopes import Escalation, ResultEnvelope, TaskEnvelope
from taxos_core.compliance.service import ComputationService, NoValidatedDataError
from taxos_core.ingestion.models import Batch, BatchStatus
from taxos_core.shared.persistence.uow import Actor


class ToolGrantError(PermissionError):
    """An agent attempted a tool it was not granted. Refused server-side, and logged —
    a denied grant is also a telemetry signal (docs/security/02 §4)."""


# Per-agent tool grants. The set is small and enumerable on purpose: a security review of
# "what can agents do" should be reading a list, not auditing a codebase. Note what is
# absent — nothing here approves, files, or sends.
GRANTS: dict[str, set[str]] = {
    "data": {"list_batches", "get_batch_stats"},
    "vat": {"run_vat_computation", "get_computation", "get_lineage"},
    "fraud": {"list_transactions", "get_batch_stats"},
    "reporting": {"get_computation", "create_work_item"},
}


def _check(agent: str, tool: str) -> None:
    if tool not in GRANTS.get(agent, set()):
        raise ToolGrantError(f"agent '{agent}' has no grant for tool '{tool}'")


class DataAgent:
    """Answers "do we have everything, and is it trustworthy?" — the go/no-go for
    computation. It interprets validation evidence; it never invents or estimates data."""

    name = "data"

    async def run(
        self, envelope: TaskEnvelope, session: AsyncSession, tenant_id, actor: Actor
    ) -> ResultEnvelope:
        started = time.monotonic()
        _check(self.name, "list_batches")

        entity_id = envelope.context_refs["entity_id"]
        period = envelope.context_refs["period_key"]
        batches = list(
            (
                await session.execute(
                    select(Batch).where(
                        Batch.entity_id == entity_id,
                        Batch.period_key == period,
                        Batch.status.in_(
                            [BatchStatus.VALIDATED, BatchStatus.VALIDATED_WITH_EXCEPTIONS]
                        ),
                    )
                )
            )
            .scalars()
            .all()
        )
        tool_calls = [
            {
                "tool": "list_batches",
                "args": {"entity_id": entity_id, "period_key": period},
                "result_count": len(batches),
            }
        ]

        sources = {b.source_type for b in batches}
        accepted = sum(b.accepted_count for b in batches)
        quarantined = sum(b.quarantined_count for b in batches)
        duration = int((time.monotonic() - started) * 1000)

        # Missing sources park the run rather than proceeding on partial data. A return
        # computed from half the evidence is worse than no return, because it looks fine.
        missing = {"AR", "AP"} - sources
        if missing:
            return ResultEnvelope(
                agent=self.name,
                status="ESCALATED",
                output={"sources_present": sorted(sources), "missing": sorted(missing)},
                tool_calls=tool_calls,
                escalation=Escalation(
                    reason=f"No validated {'/'.join(sorted(missing))} data for {period}",
                    needed_input=(
                        f"Upload the {'/'.join(sorted(missing))} extract for {period} and re-run."
                    ),
                ),
                confidence=Decimal("1.0"),
                confidence_basis="DETERMINISTIC",
                duration_ms=duration,
            )

        narrative = (
            f"{len(batches)} validated batches covering {', '.join(sorted(sources))}. "
            f"{accepted} rows accepted"
            + (
                f", {quarantined} quarantined and excluded from computation."
                if quarantined
                else " with no exceptions."
            )
        )
        return ResultEnvelope(
            agent=self.name,
            status="COMPLETED",
            output={
                "status": "READY",
                "batches": len(batches),
                "accepted_rows": accepted,
                "quarantined_rows": quarantined,
                "narrative": narrative,
            },
            tool_calls=tool_calls,
            confidence=Decimal("1.0"),
            confidence_basis="DETERMINISTIC",
            duration_ms=duration,
        )


class VatAgent:
    """Triggers the deterministic engine, then explains the result.

    The figures are the engine's. This agent's contribution is variance analysis and
    flagging judgement areas — reasoning around the arithmetic, never the arithmetic.
    """

    name = "vat"

    async def run(
        self, envelope: TaskEnvelope, session: AsyncSession, tenant_id, actor: Actor
    ) -> ResultEnvelope:
        started = time.monotonic()
        _check(self.name, "run_vat_computation")

        entity_id = envelope.context_refs["entity_id"]
        period = envelope.context_refs["period_key"]
        service = ComputationService(session, tenant_id, actor)
        try:
            computation = await service.compute_vat(entity_id=entity_id, period_key=period)
        except NoValidatedDataError as exc:
            return ResultEnvelope(
                agent=self.name,
                status="ESCALATED",
                tool_calls=[{"tool": "run_vat_computation", "error": str(exc)}],
                escalation=Escalation(
                    reason=str(exc), needed_input="Ingest validated data for the period."
                ),
                duration_ms=int((time.monotonic() - started) * 1000),
            )

        result = computation.result
        observations: list[str] = []
        if computation.unmapped_codes:
            # Unknown codes are reported for a human, never resolved by guessing.
            observations.append(
                f"{len(computation.unmapped_codes)} unrecognised VAT code(s) "
                f"({', '.join(computation.unmapped_codes)}) contributed to no box — "
                "the data or the rule pack needs a decision."
            )
        if Decimal(result.get("box_1", "0")) > 0 and Decimal(result.get("box_4", "0")) > 0:
            observations.append(
                "Reverse-charge purchases appear in both Box 1 and Box 4 per VATDSAG; "
                "they self-cancel in cash terms but both entries are required."
            )

        return ResultEnvelope(
            agent=self.name,
            status="COMPLETED",
            output={
                # Only a reference: this envelope has no numeric fields, so the agent
                # cannot author a figure even by accident.
                "computation_id": str(computation.id),
                "result_hash": computation.result_hash,
                "pack_ref": computation.pack_ref,
                "observations": observations,
                "narrative": (
                    f"VAT return computed under {computation.pack_ref}. "
                    f"Net position {result.get('box_5')} "
                    f"(output {result.get('box_1')}, input {result.get('box_4')})."
                ),
            },
            tool_calls=[
                {
                    "tool": "run_vat_computation",
                    "args": {"entity_id": entity_id, "period": period},
                    "computation_id": str(computation.id),
                }
            ],
            confidence=Decimal("1.0"),
            confidence_basis="DETERMINISTIC",
            duration_ms=int((time.monotonic() - started) * 1000),
        )


class FraudAgent:
    """Rule-based anomaly review over the validated population (docs/ml — Rung 1).

    Deliberately not a model: duplicates and round-number patterns are near-deterministic,
    and a rule that can explain itself beats a score that cannot.
    """

    name = "fraud"

    async def run(
        self, envelope: TaskEnvelope, session: AsyncSession, tenant_id, actor: Actor
    ) -> ResultEnvelope:
        started = time.monotonic()
        _check(self.name, "list_transactions")

        from taxos_core.ingestion.models import TransactionRow

        entity_id = envelope.context_refs["entity_id"]
        period = envelope.context_refs["period_key"]
        rows = list(
            (
                await session.execute(
                    select(TransactionRow)
                    .join(Batch, Batch.id == TransactionRow.batch_id)
                    .where(Batch.entity_id == entity_id, Batch.period_key == period)
                )
            )
            .scalars()
            .all()
        )

        findings: list[dict] = []
        seen: dict[tuple, str] = {}
        for row in rows:
            key = (row.counterparty, row.net_amount)
            if key in seen:
                findings.append(
                    {
                        "type": "POSSIBLE_DUPLICATE",
                        "severity": "HIGH",
                        "detail": (
                            f"{row.document_ref} matches {seen[key]}: same counterparty "
                            f"({row.counterparty}) and identical net amount."
                        ),
                    }
                )
            seen[key] = row.document_ref

            if row.net_amount % 1000 == 0 and row.net_amount >= 10000:
                # Present money at 2dp: the column is Numeric(18,4) for arithmetic
                # headroom, but "18000.0000" in a reviewer's finding reads as a defect.
                amount = f"£{row.net_amount.quantize(Decimal('0.01')):,}"
                findings.append(
                    {
                        "type": "ROUND_AMOUNT",
                        "severity": "LOW",
                        "detail": (
                            f"{row.document_ref} is an exact round amount ({amount}) — "
                            "worth a glance, commonly benign."
                        ),
                    }
                )

        return ResultEnvelope(
            agent=self.name,
            status="COMPLETED",
            output={
                "scanned": len(rows),
                "findings": findings,
                "narrative": (
                    f"Scanned {len(rows)} transactions: "
                    + (
                        f"{len(findings)} item(s) flagged for review."
                        if findings
                        else "no anomalies flagged."
                    )
                ),
            },
            tool_calls=[{"tool": "list_transactions", "result_count": len(rows)}],
            confidence=Decimal("1.0"),
            confidence_basis="DETERMINISTIC",
            duration_ms=int((time.monotonic() - started) * 1000),
        )


SPECIALISTS = {
    DataAgent.name: DataAgent(),
    VatAgent.name: VatAgent(),
    FraudAgent.name: FraudAgent(),
}
