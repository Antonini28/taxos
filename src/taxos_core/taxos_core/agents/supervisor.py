"""The Supervisor: plans, routes, tracks, and hands off (docs/ai/03 §3.1).

The invariant this file exists to hold: **a run can end in HANDOFF, WAITING_INPUT, or
FAILED — never in APPROVED.** There is no code path from here to an approval, because
approving requires a human actor passing a segregation-of-duties check in the workflow
module. The gate is structural, not a policy someone remembered to write down.

The Supervisor also never computes anything itself. It plans and routes; specialists
call tools; tools run deterministic engines.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taxos_core.agents.envelopes import TaskEnvelope
from taxos_core.agents.models import AgentRun, AgentStep, RunState
from taxos_core.agents.specialists import SPECIALISTS, ToolGrantError
from taxos_core.shared.persistence.uow import Actor, AuditedUnitOfWork
from taxos_core.workflow.service import WorkflowService
from taxos_core.workflow.states import WorkItemState

# The plan for a VAT cycle. A fixed, reviewable sequence rather than an emergent one:
# in a compliance domain, "the agent decided to try something" is a defect, not a feature.
VAT_PLAN = [
    ("data", "Confirm the data foundation for the period"),
    ("vat", "Compute the VAT return and explain the result"),
    ("fraud", "Review the transaction population for anomalies"),
    ("reporting", "Assemble the review package and hand off to a human"),
]


@dataclass
class RunOutcome:
    run: AgentRun
    steps: list[AgentStep]


class Supervisor:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID, actor: Actor) -> None:
        self._s = session
        self._tenant_id = tenant_id
        self._actor = actor  # the human who asked; agents act on their behalf

    async def start_vat_run(
        self, *, entity_id: uuid.UUID, period_key: str, goal: str | None = None
    ) -> AgentRun:
        """Create the run and its plan. Planning is a separate, audited act from execution
        so an infeasible plan is refused before anything happens."""
        plan = [{"agent": agent, "goal": step_goal} for agent, step_goal in VAT_PLAN]
        unknown = [
            step["agent"]
            for step in plan
            if step["agent"] not in SPECIALISTS and step["agent"] != "reporting"
        ]
        if unknown:
            raise ValueError(f"plan references unregistered agents: {unknown}")

        uow = AuditedUnitOfWork(self._s, self._tenant_id, self._actor)
        run = AgentRun(
            tenant_id=self._tenant_id,
            goal=goal or f"Prepare VAT return for {period_key}",
            entity_id=entity_id,
            period_key=period_key,
            state=RunState.PLANNING,
            plan=plan,
            requested_by=self._actor.ref,
            budget_steps=len(plan) + 2,
            created_by=self._actor.ref,
        )
        self._s.add(run)
        await self._s.flush()

        uow.record(
            "agent_run.planned",
            "agent_run",
            str(run.id),
            after={"goal": run.goal, "steps": len(plan), "period": period_key},
        )
        uow.publish("AgentRunRequested", {"run_id": str(run.id), "period_key": period_key})
        await uow.commit()
        return run

    async def execute(self, run_id: uuid.UUID) -> RunOutcome:
        """Execute the plan step by step, recording every step before moving on.

        Steps are persisted as they happen rather than at the end: a run that crashes
        mid-flight must still be able to show how far it got and why it stopped.
        """
        run = (await self._s.execute(select(AgentRun).where(AgentRun.id == run_id))).scalar_one()

        run.state = RunState.EXECUTING
        sequence = run.steps_used

        for step_spec in run.plan[sequence:]:
            if run.steps_used >= run.budget_steps:
                await self._fail(run, "Step budget exhausted before the plan completed", sequence)
                break

            agent_name = step_spec["agent"]
            envelope = TaskEnvelope(
                agent=agent_name,
                goal=step_spec["goal"],
                context_refs={
                    "entity_id": str(run.entity_id),
                    "period_key": run.period_key or "",
                },
            )

            if agent_name == "reporting":
                await self._handoff(run, sequence)
                break

            specialist = SPECIALISTS[agent_name]
            try:
                result = await specialist.run(envelope, self._s, self._tenant_id, self._actor)
            except ToolGrantError as exc:
                # A refused grant is a governance event, not a crash: record it and stop.
                await self._fail(run, f"Tool grant refused: {exc}", sequence)
                break

            sequence += 1
            await self._record_step(run, sequence, envelope, result)

            if result.status == "ESCALATED":
                # Park rather than guess. The run resumes from this checkpoint once a
                # human provides what was named.
                run.state = RunState.WAITING_INPUT
                run.escalation = {
                    "reason": result.escalation.reason if result.escalation else "unknown",
                    "needed_input": result.escalation.needed_input if result.escalation else "",
                    "at_step": sequence,
                }
                uow = AuditedUnitOfWork(self._s, self._tenant_id, self._actor)
                uow.record(
                    "agent_run.escalated",
                    "agent_run",
                    str(run.id),
                    after=run.escalation,
                )
                uow.publish("EscalationRaised", {"run_id": str(run.id), **run.escalation})
                await uow.commit()
                break

        steps = list(
            (
                await self._s.execute(
                    select(AgentStep).where(AgentStep.run_id == run.id).order_by(AgentStep.sequence)
                )
            )
            .scalars()
            .all()
        )
        return RunOutcome(run=run, steps=steps)

    async def _record_step(self, run, sequence, envelope, result) -> None:
        uow = AuditedUnitOfWork(self._s, self._tenant_id, self._actor)
        self._s.add(
            AgentStep(
                tenant_id=self._tenant_id,
                run_id=run.id,
                sequence=sequence,
                agent=result.agent,
                goal=envelope.goal,
                status=result.status,
                tool_calls=result.tool_calls,
                output=result.output,
                confidence=result.confidence,
                confidence_basis=result.confidence_basis,
                model=result.model,
                duration_ms=result.duration_ms,
                cost_gbp=result.cost_gbp,
            )
        )
        run.steps_used = sequence
        run.cost_gbp = Decimal(run.cost_gbp) + result.cost_gbp
        uow.record(
            "agent_step.completed",
            "agent_run",
            str(run.id),
            after={
                "sequence": sequence,
                "agent": result.agent,
                "status": result.status,
                "confidence_basis": result.confidence_basis,
            },
        )
        await uow.commit()

    async def _handoff(self, run, sequence) -> None:
        """Terminal success: a work item awaiting a human.

        Preparation is credited to the requesting human, so the SoD check downstream
        still compares two people — an agent cannot stand in for either of them.
        """
        workflow = WorkflowService(self._s, self._tenant_id, self._actor)
        computation_id = await self._latest_computation_id(run)

        item = await workflow.create_work_item(
            entity_id=run.entity_id,
            period_key=run.period_key,
            item_type="VAT_RETURN",
            title=f"VAT {run.period_key} · prepared by agent run",
            computation_id=computation_id,
            prepared_by=run.requested_by,
        )
        await workflow.transition(item.id, WorkItemState.AWAITING_REVIEW)

        uow = AuditedUnitOfWork(self._s, self._tenant_id, self._actor)
        run.work_item_id = item.id
        run.state = RunState.HANDOFF
        run.steps_used = sequence + 1
        run.finished_at = datetime.now(UTC)
        uow.record(
            "agent_run.handoff",
            "agent_run",
            str(run.id),
            after={"work_item_id": str(item.id), "state": RunState.HANDOFF},
        )
        uow.publish("AgentRunHandoff", {"run_id": str(run.id), "work_item_id": str(item.id)})
        await uow.commit()

    async def _latest_computation_id(self, run) -> uuid.UUID | None:
        from taxos_core.compliance.models import Computation

        result = await self._s.execute(
            select(Computation.id)
            .where(
                Computation.entity_id == run.entity_id,
                Computation.period_key == run.period_key,
            )
            .order_by(Computation.computed_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _fail(self, run, reason: str, sequence: int) -> None:
        uow = AuditedUnitOfWork(self._s, self._tenant_id, self._actor)
        run.state = RunState.FAILED
        run.escalation = {"reason": reason, "needed_input": "Human review of the run trace"}
        run.finished_at = datetime.now(UTC)
        uow.record("agent_run.failed", "agent_run", str(run.id), after={"reason": reason})
        uow.publish("AgentRunFailed", {"run_id": str(run.id), "reason": reason})
        await uow.commit()
