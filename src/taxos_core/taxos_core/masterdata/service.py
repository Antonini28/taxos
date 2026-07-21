"""Master data use-cases.

The reference implementation of the service pattern (Phase 6 doc 03 §2):
one service method = one UoW = one atomic, audited business action.
"""

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taxos_core.masterdata.models import LegalEntity, TaxRegistration
from taxos_core.shared.persistence.uow import Actor, AuditedUnitOfWork


class EntityService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID, actor: Actor) -> None:
        self._s = session
        self._tenant_id = tenant_id
        self._actor = actor

    async def create_entity(self, *, code: str, name: str, jurisdiction_code: str) -> LegalEntity:
        uow = AuditedUnitOfWork(self._s, self._tenant_id, self._actor)
        entity = LegalEntity(
            tenant_id=self._tenant_id,
            code=code,
            name=name,
            jurisdiction_code=jurisdiction_code,
            created_by=self._actor.ref,
        )
        self._s.add(entity)
        await self._s.flush()  # assign id without committing

        uow.record(
            "entity.created",
            "legal_entity",
            str(entity.id),
            after={"code": code, "name": name, "jurisdiction": jurisdiction_code},
        )
        uow.publish("EntityCreated", {"entity_id": str(entity.id), "code": code})
        await uow.commit()
        return entity

    async def register_for_tax(
        self,
        *,
        entity_id: uuid.UUID,
        tax_type: str,
        registration_number: str,
        effective_from: date,
    ) -> TaxRegistration:
        uow = AuditedUnitOfWork(self._s, self._tenant_id, self._actor)
        registration = TaxRegistration(
            tenant_id=self._tenant_id,
            entity_id=entity_id,
            tax_type=tax_type,
            registration_number=registration_number,
            effective_from=effective_from,
            created_by=self._actor.ref,
        )
        self._s.add(registration)
        await self._s.flush()

        uow.record(
            "registration.created",
            "tax_registration",
            str(registration.id),
            after={
                "entity_id": str(entity_id),
                "tax_type": tax_type,
                "number": registration_number,
            },
        )
        uow.publish(
            "RegistrationCreated",
            {"registration_id": str(registration.id), "entity_id": str(entity_id)},
        )
        await uow.commit()
        return registration

    async def list_entities(self) -> list[LegalEntity]:
        """Read path: RLS scopes this to the session's tenant — no WHERE clause needed,
        and none can be forgotten (ADR-006)."""
        result = await self._s.execute(select(LegalEntity).order_by(LegalEntity.code))
        return list(result.scalars().all())
