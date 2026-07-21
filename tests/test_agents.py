"""US-401: the agent run — plan, execute, escalate, hand off.

The governance invariants get their own tests here, because "agents cannot approve" is
the platform's central claim and a claim without a test is a hope.
"""

import pytest
from sqlalchemy import select, text
from taxos_core.agents.models import AgentRun, AgentStep, RunState
from taxos_core.agents.specialists import GRANTS, ToolGrantError
from taxos_core.agents.supervisor import Supervisor
from taxos_core.audit.verify import verify_chain
from taxos_core.ingestion.service import IngestionService
from taxos_core.masterdata.service import EntityService
from taxos_core.shared.persistence.uow import Actor
from taxos_core.workflow.service import SegregationOfDutiesError, WorkflowService
from taxos_core.workflow.states import WorkItemState

PREPARER = Actor.user("daniel@dev")
REVIEWER = Actor.user("priya@dev")


@pytest.fixture
async def entity_with_data(session_a, tenant_a):
    """An entity with both sales and purchases validated — a run's happy path."""
    from tests.test_computation import PURCHASE_CSV, SALES_CSV

    entity = await EntityService(session_a, tenant_a, PREPARER).create_entity(
        code="UK-01", name="Meridian UK Ltd", jurisdiction_code="UK"
    )
    ingestion = IngestionService(session_a, tenant_a, PREPARER)
    await ingestion.ingest_csv(
        entity_id=entity.id,
        period_key="2026-Q2",
        source_type="AR",
        filename="sales.csv",
        content=SALES_CSV,
    )
    await ingestion.ingest_csv(
        entity_id=entity.id,
        period_key="2026-Q2",
        source_type="AP",
        filename="purchases.csv",
        content=PURCHASE_CSV,
    )
    return entity.id


@pytest.fixture
async def entity_missing_purchases(session_a, tenant_a):
    """Sales only — the gap that should park a run rather than produce half a return."""
    from tests.test_computation import SALES_CSV

    entity = await EntityService(session_a, tenant_a, PREPARER).create_entity(
        code="UK-02", name="Meridian Services Ltd", jurisdiction_code="UK"
    )
    await IngestionService(session_a, tenant_a, PREPARER).ingest_csv(
        entity_id=entity.id,
        period_key="2026-Q2",
        source_type="AR",
        filename="sales.csv",
        content=SALES_CSV,
    )
    return entity.id


# --- the happy path -----------------------------------------------------------


async def test_run_completes_in_handoff_never_approved(session_a, tenant_a, entity_with_data):
    """THE invariant: a run's terminal success is HANDOFF. Approval is not reachable."""
    supervisor = Supervisor(session_a, tenant_a, PREPARER)
    run = await supervisor.start_vat_run(entity_id=entity_with_data, period_key="2026-Q2")
    outcome = await supervisor.execute(run.id)

    assert outcome.run.state == RunState.HANDOFF
    assert outcome.run.work_item_id is not None

    item = await WorkflowService(session_a, tenant_a, PREPARER).get(outcome.run.work_item_id)
    assert item.state == WorkItemState.AWAITING_REVIEW  # not APPROVED — a human must act


async def test_every_step_is_traced_with_its_basis(session_a, tenant_a, entity_with_data):
    supervisor = Supervisor(session_a, tenant_a, PREPARER)
    run = await supervisor.start_vat_run(entity_id=entity_with_data, period_key="2026-Q2")
    outcome = await supervisor.execute(run.id)

    assert [s.agent for s in outcome.steps] == ["data", "vat", "fraud"]
    for step in outcome.steps:
        assert step.tool_calls, f"{step.agent} recorded no tool calls"
        assert step.confidence_basis in ("DETERMINISTIC", "GROUNDED", "MODEL_JUDGEMENT")
        assert step.output


async def test_agent_output_contains_no_authored_figures(session_a, tenant_a, entity_with_data):
    """AP-2 in practice: the VAT agent returns a computation *reference*, never numbers
    of its own. The narrative quotes engine output; the schema has nowhere to invent."""
    supervisor = Supervisor(session_a, tenant_a, PREPARER)
    run = await supervisor.start_vat_run(entity_id=entity_with_data, period_key="2026-Q2")
    outcome = await supervisor.execute(run.id)

    vat_step = next(s for s in outcome.steps if s.agent == "vat")
    assert "computation_id" in vat_step.output
    assert "result_hash" in vat_step.output
    # No numeric-typed fields in the payload: every figure is a string quoted from the
    # engine's own result, reachable by following the computation reference.
    assert not any(isinstance(v, (int, float)) for v in vat_step.output.values())


# --- escalation ---------------------------------------------------------------


async def test_missing_data_parks_the_run_and_names_the_gap(
    session_a, tenant_a, entity_missing_purchases
):
    """The run does not guess, does not estimate, and does not half-compute."""
    supervisor = Supervisor(session_a, tenant_a, PREPARER)
    run = await supervisor.start_vat_run(entity_id=entity_missing_purchases, period_key="2026-Q2")
    outcome = await supervisor.execute(run.id)

    assert outcome.run.state == RunState.WAITING_INPUT
    assert outcome.run.work_item_id is None  # nothing handed to a human to approve
    assert "AP" in outcome.run.escalation["reason"]
    assert "Upload" in outcome.run.escalation["needed_input"]

    escalated = [s for s in outcome.steps if s.status == "ESCALATED"]
    assert len(escalated) == 1 and escalated[0].agent == "data"


async def test_a_parked_run_produced_no_computation(session_a, tenant_a, entity_missing_purchases):
    from taxos_core.compliance.models import Computation

    supervisor = Supervisor(session_a, tenant_a, PREPARER)
    run = await supervisor.start_vat_run(entity_id=entity_missing_purchases, period_key="2026-Q2")
    await supervisor.execute(run.id)

    computations = (await session_a.execute(select(Computation))).scalars().all()
    assert computations == []


# --- capability confinement ---------------------------------------------------


async def test_agents_have_no_grant_for_approval_or_filing():
    """Enumerable by design: the whole grant surface fits in one assertion."""
    all_grants = {tool for grants in GRANTS.values() for tool in grants}
    forbidden = {"approve", "grant_approval", "file_return", "submit", "send_email", "delete"}
    assert all_grants & forbidden == set()


async def test_undeclared_tool_is_refused(session_a, tenant_a, entity_with_data):
    """The check is server-side and raises rather than warning — a refused grant stops work."""
    from taxos_core.agents.specialists import _check

    _check("vat", "run_vat_computation")  # granted
    with pytest.raises(ToolGrantError, match="no grant"):
        _check("vat", "list_transactions")  # the fraud agent's tool, not the VAT agent's


async def test_agent_prepared_work_still_blocks_the_requester_from_approving(
    session_a, tenant_a, entity_with_data
):
    """An agent run cannot be used to launder segregation of duties: the requesting human
    owns preparation, so they still cannot approve what they asked for."""
    supervisor = Supervisor(session_a, tenant_a, PREPARER)
    run = await supervisor.start_vat_run(entity_id=entity_with_data, period_key="2026-Q2")
    outcome = await supervisor.execute(run.id)

    workflow = WorkflowService(session_a, tenant_a, PREPARER)
    item = await workflow.get(outcome.run.work_item_id)
    with pytest.raises(SegregationOfDutiesError):
        await workflow.approve(item.id, content_hash=item.content_hash)

    # A different human can, which is the whole point of the gate.
    reviewer = WorkflowService(session_a, tenant_a, REVIEWER)
    approved = await reviewer.approve(item.id, content_hash=item.content_hash)
    assert approved.approval.approver == "user:priya@dev"


# --- budgets, audit, immutability ---------------------------------------------


async def test_step_budget_exhaustion_fails_the_run(session_a, tenant_a, entity_with_data):
    supervisor = Supervisor(session_a, tenant_a, PREPARER)
    run = await supervisor.start_vat_run(entity_id=entity_with_data, period_key="2026-Q2")
    run.budget_steps = 1  # cannot complete the plan
    await session_a.flush()

    outcome = await supervisor.execute(run.id)
    assert outcome.run.state == RunState.FAILED
    assert "budget" in outcome.run.escalation["reason"].lower()


async def test_run_is_audited_and_the_chain_still_verifies(session_a, tenant_a, entity_with_data):
    from taxos_core.audit.models import AuditEvent

    supervisor = Supervisor(session_a, tenant_a, PREPARER)
    run = await supervisor.start_vat_run(entity_id=entity_with_data, period_key="2026-Q2")
    await supervisor.execute(run.id)

    actions = {a.action for a in (await session_a.execute(select(AuditEvent))).scalars().all()}
    assert {"agent_run.planned", "agent_step.completed", "agent_run.handoff"} <= actions
    assert (await verify_chain(session_a, tenant_a)).verified is True


async def test_agent_steps_are_immutable(session_a, tenant_a, entity_with_data):
    supervisor = Supervisor(session_a, tenant_a, PREPARER)
    run = await supervisor.start_vat_run(entity_id=entity_with_data, period_key="2026-Q2")
    await supervisor.execute(run.id)

    with pytest.raises(Exception, match="append-only"):
        await session_a.execute(text("UPDATE agent_step SET output = '{}'::jsonb"))
    await session_a.rollback()


async def test_runs_are_tenant_isolated(session_a, session_b, tenant_a, entity_with_data):
    supervisor = Supervisor(session_a, tenant_a, PREPARER)
    await supervisor.start_vat_run(entity_id=entity_with_data, period_key="2026-Q2")

    assert (await session_b.execute(select(AgentRun))).scalars().all() == []
    assert (await session_b.execute(select(AgentStep))).scalars().all() == []
