"""US-101 skeleton verification: app factory, health endpoints, middleware, error shape."""

import httpx
import pytest
from taxos_api.main import DomainError, create_app
from taxos_core.shared.config import Settings


@pytest.fixture
def app():
    return create_app(Settings(env="ci"))


async def _client(app) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def test_healthz_ok(app):
    async with await _client(app) as c:
        r = await c.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_request_id_and_security_headers(app):
    async with await _client(app) as c:
        r = await c.get("/healthz", headers={"X-Request-ID": "test-123"})
    assert r.headers["X-Request-ID"] == "test-123"
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"


async def test_domain_error_renders_problem_json(app):
    @app.get("/boom")
    async def boom():
        raise DomainError("something broke")

    async with await _client(app) as c:
        r = await c.get("/boom")
    assert r.status_code == 500
    assert r.headers["content-type"].startswith("application/problem+json")
    body = r.json()
    assert body["title"] == "Internal error"
    assert body["trace_id"]  # request id propagated into the problem


def test_prod_config_fails_closed():
    with pytest.raises(ValueError, match="expose_openapi"):
        Settings(env="prod", expose_openapi=True)
