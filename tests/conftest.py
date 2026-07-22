"""Test fixtures. Every DB fixture seeds TWO tenants by default (Phase 10 doc 01 §4)
so cross-tenant assertions are always one line away."""

import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from taxos_core.shared.config import Settings
from taxos_core.shared.persistence.session import tenant_session

TENANT_A = uuid.UUID("00000000-0000-0000-0000-00000000000a")
TENANT_B = uuid.UUID("00000000-0000-0000-0000-00000000000b")

# Shared CSV fixtures. These live here rather than in a test module so suites never
# import each other — the generator (tools/seed) will supersede them at scale.
_HEADER = "document_ref,document_date,counterparty,net_amount,vat_amount,vat_code,currency\n"

CLEAN_CSV = (
    _HEADER
    + "INV-001,2026-04-15,Apex Supplies Ltd,1000.00,200.00,S20,GBP\n"
    + "INV-002,2026-05-02,Borough Print Co,500.00,100.00,S20,GBP\n"
    + "INV-003,2026-05-20,Cargo Freight Ltd,2500.00,0.00,Z00,GBP\n"
    + "INV-004,2026-06-11,Delta Construction,4000.00,0.00,RC20,GBP\n"
).encode()

# One row per failure class, so rule coverage is visible at a glance.
DIRTY_CSV = (
    _HEADER
    + "INV-010,2026-04-15,Apex Supplies Ltd,1000.00,200.00,S20,GBP\n"  # valid
    + "INV-011,2026-04-16,Bad Code Ltd,1000.00,200.00,XX9,GBP\n"  # ING-005 unknown code
    + "INV-012,2026-01-05,Wrong Period Ltd,800.00,160.00,S20,GBP\n"  # ING-003 outside period
    + "INV-013,2026-05-01,Bad Vat Ltd,1000.00,50.00,S20,GBP\n"  # ING-006 inconsistent VAT
    + ",2026-05-02,No Ref Ltd,100.00,20.00,S20,GBP\n"  # ING-001 missing field
    + "INV-015,2026-05-03,Bad Amount Ltd,not-a-number,20.00,S20,GBP\n"  # ING-004 non-numeric
).encode()


def _test_dsn(dsn: str) -> str:
    """Point at `taxos_test`, never the application database.

    The suite truncates tables between tests. Running it against the app's database
    destroys whatever is there — which it did, once, and this rewrite is why it cannot
    happen again.

    The rewrite preserves the *role* and only swaps the database name. That matters: the
    app engine connects as the non-superuser app role (so RLS is genuinely exercised) and
    the admin engine as the owner (so it can TRUNCATE). An earlier version accepted a
    single env override for the whole DSN, which silently connected the owner engine as
    the app role and broke TRUNCATE in CI — so the override is now host-only.
    """
    host_override = os.environ.get("TAXOS_TEST_DB_HOST")
    base, _, name = dsn.rpartition("/")
    if not name.startswith("taxos_test"):
        base = f"{base}/taxos_test"
    else:
        base = dsn
    if host_override:
        # Replace only the host:port segment, keeping user, password, and database.
        prefix, _, rest = base.partition("@")
        _, _, tail = rest.partition("/")
        return f"{prefix}@{host_override}/{tail}"
    return base


@pytest_asyncio.fixture
async def engine():
    """Real Postgres as the APPLICATION role — RLS only proves anything under the role
    the app actually uses (superusers bypass it). Triggers and constraints likewise."""
    eng = create_async_engine(_test_dsn(Settings().database.dsn.get_secret_value()), poolclass=None)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def admin_engine():
    """Owner role — fixture setup/teardown only (TRUNCATE, trigger toggling in tamper tests)."""
    eng = create_async_engine(
        _test_dsn(Settings().database.migration_dsn.get_secret_value()), poolclass=None
    )
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def clean_db(engine, admin_engine):
    """Truncate business tables between tests (owner role). Audit is append-only, so we
    use TRUNCATE rather than DELETE — the guard against UPDATE/DELETE is tested elsewhere."""
    async with admin_engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE anomaly, anomaly_scan, agent_step, agent_run, approval, "
                "workflow_transition, work_item, "
                "computation_line_source, computation_line, computation, "
                "validation_result, quarantine_row, transaction_row, batch, "
                "audit_event, outbox_event, tax_registration, legal_entity, tenant "
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
def clean_csv() -> bytes:
    return CLEAN_CSV


@pytest.fixture
def dirty_csv() -> bytes:
    return DIRTY_CSV


@pytest.fixture
def tenant_a() -> uuid.UUID:
    return TENANT_A


@pytest.fixture
def tenant_b() -> uuid.UUID:
    return TENANT_B
