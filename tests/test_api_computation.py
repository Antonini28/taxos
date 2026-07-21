"""API-level tests for computation and lineage."""

import httpx
import pytest
from taxos_api.deps import db_session
from taxos_api.main import create_app
from taxos_core.ingestion.service import IngestionService
from taxos_core.masterdata.service import EntityService
from taxos_core.shared.config import Settings
from taxos_core.shared.persistence.uow import Actor

from tests.test_computation import PURCHASE_CSV, SALES_CSV

ACTOR = Actor.user("daniel@dev")


@pytest.fixture
async def api(clean_db, tenant_a, session_a):
    app = create_app(Settings(env="ci"))
    app.dependency_overrides[db_session] = lambda: session_a
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"X-Taxos-Tenant": str(tenant_a), "X-Taxos-User": "daniel@dev"},
    ) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
async def entity_with_data(session_a, tenant_a):
    entity = await EntityService(session_a, tenant_a, ACTOR).create_entity(
        code="UK-01", name="Meridian UK Ltd", jurisdiction_code="UK"
    )
    ingestion = IngestionService(session_a, tenant_a, ACTOR)
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


async def test_run_computation_returns_nine_boxes(api, entity_with_data):
    response = await api.post(
        "/api/v1/computations",
        json={"entity_id": str(entity_with_data), "period_key": "2026-Q2"},
    )
    assert response.status_code == 201
    body = response.json()
    assert len(body["boxes"]) == 9
    assert body["pack_ref"] == "uk-vat@1.0.0"
    assert body["result_hash"] and body["inputs_hash"]

    boxes = {b["box_id"]: b["value"] for b in body["boxes"]}
    assert boxes["box_1"] == "3800.0000"
    assert boxes["box_4"] == "1400.0000"
    assert all(isinstance(v, str) for v in boxes.values())  # never floats on the wire


async def test_lineage_endpoint_reconciles_to_the_box(api, entity_with_data):
    created = await api.post(
        "/api/v1/computations",
        json={"entity_id": str(entity_with_data), "period_key": "2026-Q2"},
    )
    computation_id = created.json()["id"]

    response = await api.get(f"/api/v1/computations/{computation_id}/boxes/box_4/lineage")
    assert response.status_code == 200
    body = response.json()

    from decimal import Decimal

    assert Decimal(body["contribution_total"]) == Decimal(body["box_value"])
    assert body["entries"]
    assert all(entry["citation_ref"] for entry in body["entries"])
    assert {e["document_ref"] for e in body["entries"]} == {"PI-001", "PI-002"}


async def test_computation_without_data_returns_422(api, session_a, tenant_a):
    entity = await EntityService(session_a, tenant_a, ACTOR).create_entity(
        code="UK-99", name="Dormant Ltd", jurisdiction_code="UK"
    )
    response = await api.post(
        "/api/v1/computations", json={"entity_id": str(entity.id), "period_key": "2026-Q2"}
    )
    assert response.status_code == 422
    assert "No validated batches" in response.json()["detail"]


async def test_malformed_period_key_is_rejected_by_the_contract(api, entity_with_data):
    response = await api.post(
        "/api/v1/computations",
        json={"entity_id": str(entity_with_data), "period_key": "Q2-2026"},
    )
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["errors"]


async def test_unknown_box_returns_404(api, entity_with_data):
    created = await api.post(
        "/api/v1/computations",
        json={"entity_id": str(entity_with_data), "period_key": "2026-Q2"},
    )
    computation_id = created.json()["id"]
    response = await api.get(f"/api/v1/computations/{computation_id}/boxes/box_99/lineage")
    assert response.status_code == 404
