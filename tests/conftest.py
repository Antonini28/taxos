"""Test fixtures. Every DB fixture seeds TWO tenants by default (Phase 10 doc 01 §4)
so cross-tenant assertions are always one line away."""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from taxos_core.shared.config import Settings
from taxos_core.shared.persistence.session import tenant_session

TENANT_A = uuid.UUID("00000000-0000-0000-0000-00000000000a")
TENANT_B = uuid.UUID("00000000-0000-0000-0000-00000000000b")


@pytest_asyncio.fixture
async def engine():
    """Real Postgres as the APPLICATION role — RLS only proves anything under the role
    the app actually uses (superusers bypass it). Triggers and constraints likewise."""
    eng = create_async_engine(Settings().database.dsn.get_secret_value(), poolclass=None)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def admin_engine():
    """Owner role — fixture setup/teardown only (TRUNCATE, trigger toggling in tamper tests)."""
    eng = create_async_engine(Settings().database.migration_dsn.get_secret_value(), poolclass=None)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def clean_db(engine, admin_engine):
    """Truncate business tables between tests (owner role). Audit is append-only, so we
    use TRUNCATE rather than DELETE — the guard against UPDATE/DELETE is tested elsewhere."""
    async with admin_engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE audit_event, outbox_event, tax_registration, legal_entity, tenant "
                "RESTART IDENTITY CASCADE"
            )
        )
        for tid, slug in ((TENANT_A, "tenant-a"), (TENANT_B, "tenant-b")):
            await conn.execute(
                text(
                    "INSERT INTO tenant (id, name, slug, created_by) "
                    "VALUES (:id, :name, :slug, 'system:test')"
                ),
                {"id": tid, "name": slug, "slug": slug},
            )
    yield engine


@pytest_asyncio.fixture
async def session_a(clean_db):
    async with tenant_session(TENANT_A, engine=clean_db) as s:
        yield s


@pytest_asyncio.fixture
async def session_b(clean_db):
    async with tenant_session(TENANT_B, engine=clean_db) as s:
        yield s


@pytest.fixture
def tenant_a() -> uuid.UUID:
    return TENANT_A


@pytest.fixture
def tenant_b() -> uuid.UUID:
    return TENANT_B
