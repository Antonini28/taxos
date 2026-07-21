"""Request dependencies.

US-101/201 scope: tenant context and actor come from a development header. The OIDC/BFF
flow (ADR-007) replaces `current_principal` here without touching any router — which is
why routers depend on this abstraction rather than on headers.
"""

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from taxos_core.shared.config import Settings
from taxos_core.shared.persistence.session import tenant_session
from taxos_core.shared.persistence.uow import Actor


@dataclass(frozen=True)
class Principal:
    tenant_id: uuid.UUID
    actor: Actor


async def current_principal(
    request: Request,
    x_taxos_tenant: str = Header(...),
    x_taxos_user: str = Header(...),
) -> Principal:
    settings: Settings = request.app.state.settings
    if settings.env == "prod":  # pragma: no cover - guarded by config validation too
        raise RuntimeError("Header-based identity is not permitted in production")
    return Principal(tenant_id=uuid.UUID(x_taxos_tenant), actor=Actor.user(x_taxos_user))


async def db_session(
    principal: Annotated[Principal, Depends(current_principal)],
) -> AsyncIterator[AsyncSession]:
    """Every request runs inside a tenant-scoped session — RLS applies to all of it.

    The principal must be declared with `Depends`: without it FastAPI treats the
    parameter as a query field and rejects every request with a 422.
    """
    async with tenant_session(principal.tenant_id) as session:
        yield session
