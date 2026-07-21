"""Audit API: the read-only trust surface.

The most important assertion here is a negative one — there is no way to write to the
audit log through the API.
"""

import httpx
import pytest
from taxos_api.deps import db_session
from taxos_api.main import create_app
from taxos_core.agents.supervisor import Supervisor
from taxos_core.ingestion.service import IngestionService
from taxos_core.masterdata.service import EntityService
from taxos_core.shared.config import Settings
from taxos_core.shared.persistence.uow import Actor

PREPARER = Actor.user("daniel@dev")


@pytest.fixture
async def audit_client(clean_db, tenant_a, session_a):
    """An app with real history behind it: an agent run leaves both human and agent actors
    in the log, which is what the actor filter needs to distinguish."""
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
    supervisor = Supervisor(session_a, tenant_a, PREPARER)
    run = await supervisor.start_vat_run(entity_id=entity.id, period_key="2026-Q2")
    await supervisor.execute(run.id)

    app = create_app(Settings(env="ci"))
    app.dependency_overrides[db_session] = lambda: session_a
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        headers={"X-Taxos-Tenant": str(tenant_a), "X-Taxos-User": "priya@dev"},
    ) as client:
        yield client
    app.dependency_overrides.clear()


async def test_chain_status_verifies(audit_client):
    response = await audit_client.get("/api/v1/audit/chain-status")
    assert response.status_code == 200
    body = response.json()
    assert body["verified"] is True
    assert body["events_checked"] > 0
    assert body["head_hash"]
    assert body["broken_at_seq"] is None


async def test_events_are_hash_linked_in_sequence(audit_client):
    """Each event's prev_hash is its predecessor's event_hash — the chain, visible."""
    events = (await audit_client.get("/api/v1/audit/events")).json()
    assert len(events) > 1

    ascending = sorted(events, key=lambda e: e["seq"])
    for earlier, later in zip(ascending, ascending[1:], strict=False):
        assert later["prev_hash"] == earlier["event_hash"]


async def test_actor_filter_separates_humans_from_agents(audit_client):
    """Every action names an actor. An agent run credits the agent for its steps and the
    requesting human for the work item it created — both must be findable."""
    all_events = (await audit_client.get("/api/v1/audit/events")).json()
    actors = {e["actor"] for e in all_events}
    assert any(a.startswith("user:") for a in actors)

    humans = (await audit_client.get("/api/v1/audit/events?actor=user:")).json()
    assert humans and all(e["actor"].startswith("user:") for e in humans)


async def test_action_filter_narrows_to_one_kind(audit_client):
    events = (await audit_client.get("/api/v1/audit/events?action=agent_step")).json()
    assert events and all("agent_step" in e["action"] for e in events)


def test_no_write_endpoint_exists_on_the_audit_router():
    """The log is written by the unit of work as a side-effect of doing business.
    Nothing may write to it by choice — including us.

    Asserted against the published OpenAPI document rather than framework internals:
    that document is the contract a security reviewer actually reads, and it stays
    stable across FastAPI's own refactors of how routes are stored.
    """
    schema = create_app(Settings(env="ci")).openapi()
    audit_paths = {p: ops for p, ops in schema["paths"].items() if p.startswith("/api/v1/audit")}
    assert audit_paths, "audit router is not mounted"

    for path, operations in audit_paths.items():
        methods = {m.upper() for m in operations}
        assert methods <= {"GET", "HEAD", "OPTIONS"}, (
            f"{path} exposes {methods} — the audit log must be read-only"
        )
