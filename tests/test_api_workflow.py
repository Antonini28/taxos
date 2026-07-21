"""API-level tests for the approval gate — including the refusals a reviewer sees."""

import httpx
import pytest
from taxos_api.deps import db_session
from taxos_api.main import create_app
from taxos_core.compliance.service import ComputationService
from taxos_core.ingestion.service import IngestionService
from taxos_core.masterdata.service import EntityService
from taxos_core.shared.config import Settings
from taxos_core.shared.persistence.uow import Actor

from tests.test_computation import PURCHASE_CSV, SALES_CSV

PREPARER = Actor.user("daniel@dev")
REVIEWER = Actor.user("priya@dev")


def _client(app, tenant_a, user: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        headers={"X-Taxos-Tenant": str(tenant_a), "X-Taxos-User": user},
    )


@pytest.fixture
async def app_and_item(clean_db, tenant_a, session_a):
    """An app wired to the test session, plus a work item awaiting review."""
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
    computation = await ComputationService(session_a, tenant_a, PREPARER).compute_vat(
        entity_id=entity.id, period_key="2026-Q2"
    )

    app = create_app(Settings(env="ci"))
    app.dependency_overrides[db_session] = lambda: session_a

    async with _client(app, tenant_a, "daniel@dev") as preparer_client:
        created = await preparer_client.post(
            "/api/v1/work-items",
            json={
                "entity_id": str(entity.id),
                "period_key": "2026-Q2",
                "item_type": "VAT_RETURN",
                "title": "UK-01 · VAT Q2-2026",
                "computation_id": str(computation.id),
            },
        )
        item_id = created.json()["id"]
        await preparer_client.post(
            f"/api/v1/work-items/{item_id}/transitions", json={"to_state": "AWAITING_REVIEW"}
        )

    yield app, item_id, tenant_a
    app.dependency_overrides.clear()


async def test_reviewer_sees_eligibility_and_can_approve(app_and_item):
    app, item_id, tenant_a = app_and_item

    async with _client(app, tenant_a, "priya@dev") as reviewer:
        eligibility = (
            await reviewer.get(f"/api/v1/work-items/{item_id}/approval-eligibility")
        ).json()
        assert eligibility["can_approve"] is True
        assert eligibility["content_hash"]

        response = await reviewer.post(
            f"/api/v1/work-items/{item_id}/approvals",
            json={"content_hash": eligibility["content_hash"], "comment": "Lineage checked."},
        )
        assert response.status_code == 201
        assert response.json()["approver"] == "user:priya@dev"

        item = (await reviewer.get(f"/api/v1/work-items/{item_id}")).json()
        assert item["state"] == "APPROVED"


async def test_preparer_approval_returns_403_with_the_reason(app_and_item):
    """The refusal is explanatory, not a bare denial — the reviewer must know why."""
    app, item_id, tenant_a = app_and_item

    async with _client(app, tenant_a, "daniel@dev") as preparer:
        eligibility = (
            await preparer.get(f"/api/v1/work-items/{item_id}/approval-eligibility")
        ).json()
        assert eligibility["can_approve"] is False
        assert "prepared this item" in eligibility["reason"]

        response = await preparer.post(
            f"/api/v1/work-items/{item_id}/approvals",
            json={"content_hash": eligibility["content_hash"]},
        )
        assert response.status_code == 403
        assert response.headers["content-type"].startswith("application/problem+json")
        assert "second reviewer" in response.json()["detail"]


async def test_stale_hash_returns_409(app_and_item):
    app, item_id, tenant_a = app_and_item
    async with _client(app, tenant_a, "priya@dev") as reviewer:
        response = await reviewer.post(
            f"/api/v1/work-items/{item_id}/approvals", json={"content_hash": "0" * 64}
        )
        assert response.status_code == 409
        assert "changed since you opened" in response.json()["detail"]


async def test_illegal_transition_returns_409_naming_what_is_allowed(app_and_item):
    app, item_id, tenant_a = app_and_item
    async with _client(app, tenant_a, "daniel@dev") as preparer:
        await preparer.post(
            f"/api/v1/work-items/{item_id}/transitions", json={"to_state": "CANCELLED"}
        )
        response = await preparer.post(
            f"/api/v1/work-items/{item_id}/transitions", json={"to_state": "AWAITING_REVIEW"}
        )
        assert response.status_code == 409
        assert "Cannot move work item from CANCELLED" in response.json()["detail"]


async def test_history_endpoint_shows_the_full_chain(app_and_item):
    app, item_id, tenant_a = app_and_item
    async with _client(app, tenant_a, "priya@dev") as reviewer:
        eligibility = (
            await reviewer.get(f"/api/v1/work-items/{item_id}/approval-eligibility")
        ).json()
        await reviewer.post(
            f"/api/v1/work-items/{item_id}/approvals",
            json={"content_hash": eligibility["content_hash"], "comment": "ok"},
        )
        history = (await reviewer.get(f"/api/v1/work-items/{item_id}/history")).json()

    assert [(h["from_state"], h["to_state"]) for h in history] == [
        ("DRAFT", "AWAITING_REVIEW"),
        ("AWAITING_REVIEW", "APPROVED"),
    ]
    assert history[0]["actor"] == "user:daniel@dev"
    assert history[1]["actor"] == "user:priya@dev"
