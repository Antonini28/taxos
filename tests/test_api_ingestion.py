"""API-level tests for ingestion: contracts, status codes, problem+json shape."""

import httpx
import pytest
from taxos_api.deps import db_session
from taxos_api.main import create_app
from taxos_core.masterdata.service import EntityService
from taxos_core.shared.config import Settings
from taxos_core.shared.persistence.uow import Actor

ACTOR = Actor.user("daniel@dev")


@pytest.fixture
async def api_client(clean_db, tenant_a, session_a):
    """The app under test, with its session dependency overridden to the test's own
    session — so assertions and requests share one transaction and one event loop."""
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
async def api_entity_id(session_a, tenant_a):
    entity = await EntityService(session_a, tenant_a, ACTOR).create_entity(
        code="UK-01", name="Meridian UK Ltd", jurisdiction_code="UK"
    )
    return entity.id


async def _upload(client, entity_id, content, filename="ap_q2.csv", period="2026-Q2"):
    return await client.post(
        "/api/v1/batches",
        data={"entity_id": str(entity_id), "period_key": period, "source_type": "AP"},
        files={"file": (filename, content, "text/csv")},
    )


async def test_upload_returns_202_with_batch_id(api_client, api_entity_id, clean_csv):
    response = await _upload(api_client, api_entity_id, clean_csv)
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "VALIDATED"
    assert body["batch_id"]


async def test_validation_report_exposes_rule_breakdown(api_client, api_entity_id, dirty_csv):
    upload = await _upload(api_client, api_entity_id, dirty_csv, filename="dirty.csv")
    batch_id = upload.json()["batch_id"]

    report = await api_client.get(f"/api/v1/batches/{batch_id}/validation-report")
    assert report.status_code == 200
    body = report.json()
    assert body["status"] == "VALIDATED_WITH_EXCEPTIONS"
    assert body["quarantined_count"] == 5
    assert "ING-005" in body["rule_breakdown"]
    # Money crosses the wire as a decimal string — never a float (contract rule)
    assert isinstance(body["control_total"], str)


async def test_quarantine_endpoint_returns_reasons(api_client, api_entity_id, dirty_csv):
    upload = await _upload(api_client, api_entity_id, dirty_csv, filename="dirty.csv")
    batch_id = upload.json()["batch_id"]

    quarantine = await api_client.get(f"/api/v1/batches/{batch_id}/quarantine")
    assert quarantine.status_code == 200
    rows = quarantine.json()
    assert len(rows) == 5
    assert all(row["failures"][0]["message"] for row in rows)


async def test_duplicate_upload_returns_409_problem_json(api_client, api_entity_id, clean_csv):
    await _upload(api_client, api_entity_id, clean_csv)
    duplicate = await _upload(api_client, api_entity_id, clean_csv, filename="renamed.csv")

    assert duplicate.status_code == 409
    assert duplicate.headers["content-type"].startswith("application/problem+json")
    body = duplicate.json()
    assert body["type"].endswith("duplicate-content")
    assert "already ingested" in body["detail"]
    assert body["trace_id"]


async def test_empty_file_is_rejected_with_422(api_client, api_entity_id):
    response = await _upload(api_client, api_entity_id, b"", filename="empty.csv")
    assert response.status_code == 422
    assert response.json()["type"].endswith("validation")


async def test_unknown_batch_returns_404(api_client):
    response = await api_client.get(
        "/api/v1/batches/00000000-0000-0000-0000-0000000000ff/validation-report"
    )
    assert response.status_code == 404
    assert response.json()["title"] == "Resource not found"
