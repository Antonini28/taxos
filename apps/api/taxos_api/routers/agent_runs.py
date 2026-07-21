"""Agent run endpoints (US-401).

Note what is absent: there is no endpoint here that approves anything. A run's terminal
success is a work item awaiting a human, and approving it happens through the workflow
router under a segregation-of-duties check.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from taxos_core.agents.models import AgentRun, AgentStep
from taxos_core.agents.supervisor import Supervisor

from taxos_api.deps import Principal, current_principal, db_session
from taxos_api.errors import NotFoundError, ValidationFailed

router = APIRouter(prefix="/agent-runs", tags=["agents"])

PrincipalDep = Annotated[Principal, Depends(current_principal)]
SessionDep = Annotated[AsyncSession, Depends(db_session)]


class StartRunRequest(BaseModel):
    entity_id: uuid.UUID
    period_key: str = Field(pattern=r"^\d{4}-Q[1-4]$")
    goal: str | None = None


class StepOut(BaseModel):
    sequence: int
    agent: str
    goal: str
    status: str
    tool_calls: list[dict]
    output: dict
    confidence: str
    confidence_basis: str
    model: str
    duration_ms: int


class RunOut(BaseModel):
    id: uuid.UUID
    goal: str
    state: str
    plan: list[dict]
    requested_by: str
    work_item_id: uuid.UUID | None
    escalation: dict | None
    steps_used: int
    budget_steps: int
    cost_gbp: str
    mode: str
    steps: list[StepOut] = []


def _run_out(run: AgentRun, steps: list[AgentStep]) -> RunOut:
    return RunOut(
        id=run.id,
        goal=run.goal,
        state=run.state,
        plan=run.plan,
        requested_by=run.requested_by,
        work_item_id=run.work_item_id,
        escalation=run.escalation,
        steps_used=run.steps_used,
        budget_steps=run.budget_steps,
        cost_gbp=str(run.cost_gbp),
        mode=run.mode,
        steps=[
            StepOut(
                sequence=s.sequence,
                agent=s.agent,
                goal=s.goal,
                status=s.status,
                tool_calls=s.tool_calls,
                output=s.output,
                confidence=str(s.confidence),
                confidence_basis=s.confidence_basis,
                model=s.model,
                duration_ms=s.duration_ms,
            )
            for s in steps
        ],
    )


@router.post("", response_model=RunOut, status_code=status.HTTP_201_CREATED)
async def start_run(body: StartRunRequest, principal: PrincipalDep, session: SessionDep) -> RunOut:
    """Plan and execute a run. Synchronous here because the work is fast and
    deterministic; the architecture's async path is what a live-model runtime needs."""
    supervisor = Supervisor(session, principal.tenant_id, principal.actor)
    try:
        run = await supervisor.start_vat_run(
            entity_id=body.entity_id, period_key=body.period_key, goal=body.goal
        )
    except ValueError as exc:
        raise ValidationFailed(str(exc)) from exc

    outcome = await supervisor.execute(run.id)
    return _run_out(outcome.run, outcome.steps)


@router.get("", response_model=list[RunOut])
async def list_runs(principal: PrincipalDep, session: SessionDep) -> list[RunOut]:
    runs = list(
        (await session.execute(select(AgentRun).order_by(AgentRun.created_at.desc()).limit(20)))
        .scalars()
        .all()
    )
    return [_run_out(run, []) for run in runs]


@router.get("/{run_id}", response_model=RunOut)
async def get_run(run_id: uuid.UUID, principal: PrincipalDep, session: SessionDep) -> RunOut:
    run = (
        await session.execute(select(AgentRun).where(AgentRun.id == run_id))
    ).scalar_one_or_none()
    if run is None:
        raise NotFoundError(f"Agent run {run_id} not found")
    steps = list(
        (
            await session.execute(
                select(AgentStep).where(AgentStep.run_id == run_id).order_by(AgentStep.sequence)
            )
        )
        .scalars()
        .all()
    )
    return _run_out(run, steps)
