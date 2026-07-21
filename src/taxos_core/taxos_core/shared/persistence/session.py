"""Session factories with RLS tenancy (Phase 6 doc 03 §1; ADR-006).

`set_config(..., true)` is TRANSACTION-LOCAL — this is what prevents tenant context
leaking across pooled connections, the classic RLS-with-pooling bug.
"""

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from taxos_core.shared.config import Settings

_engine: AsyncEngine | None = None


def get_engine(settings: Settings | None = None) -> AsyncEngine:
    global _engine
    if _engine is None:
        s = settings or Settings()
        _engine = create_async_engine(
            s.database.dsn.get_secret_value(),
            pool_size=s.database.pool_size,
            pool_pre_ping=True,
            connect_args={
                "server_settings": {"statement_timeout": str(s.database.statement_timeout_ms)}
            },
        )
    return _engine


async def dispose_engine() -> None:
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None


@asynccontextmanager
async def tenant_session(
    tenant_id: uuid.UUID, engine: AsyncEngine | None = None
) -> AsyncIterator[AsyncSession]:
    """Every business query runs inside one of these. Without the tenant GUC set,
    RLS policies match nothing — the app fails closed by construction.

    The GUC is set on EVERY transaction begin, not once per session: `set_config(...,
    true)` is transaction-local (that locality is what stops tenant context leaking
    across pooled connections), so a session that commits and continues would
    otherwise run its next statements with no tenant context — and see nothing.
    """
    eng = engine or get_engine()
    session = AsyncSession(eng, expire_on_commit=False)

    @event.listens_for(session.sync_session, "after_begin")
    def _set_tenant(sync_session, transaction, connection) -> None:  # noqa: ANN001
        connection.exec_driver_sql(f"SET LOCAL app.tenant_id = '{tenant_id}'")

    try:
        await session.execute(text("SELECT 1"))  # force begin so the GUC is set immediately
        yield session
    finally:
        await session.close()


@asynccontextmanager
async def platform_session(engine: AsyncEngine | None = None) -> AsyncIterator[AsyncSession]:
    """Cross-tenant infrastructure only (outbox relay, platform metrics).

    Deliberately separate and named so its use is greppable in review.
    """
    eng = engine or get_engine()
    async with AsyncSession(eng, expire_on_commit=False) as session:
        yield session
