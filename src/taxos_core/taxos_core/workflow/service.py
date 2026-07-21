"""Workflow use-cases — the approval gate (US-402, GP-1).

Three rules are enforced here and nowhere else, so there is one place to read them:

  1. Only legal transitions occur (states.py holds the map).
  2. Segregation of duties: the approver may not be the preparer.
  3. An approval binds to a content hash. If the underlying computation changes, the
     approval is void and the item returns to preparation — automatically, not by
     anyone remembering to do it.
"""

import hashlib
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taxos_core.audit.hashing import canonical_json
from taxos_core.compliance.models import Computation
from taxos_core.shared.persistence.base import utcnow
from taxos_core.shared.persistence.uow import Actor, AuditedUnitOfWork
from taxos_core.workflow.models import Approval, WorkflowTransition, WorkItem
from taxos_core.workflow.states import WorkItemState, assert_legal


class SegregationOfDutiesError(Exception):
    """The preparer cannot approve their own work. Not configurable."""


class StaleContentError(Exception):
    """The content changed since the reviewer last saw it — approving now would attest
    to something they have not read."""


class NotReviewableError(Exception):
    """The item is not in a state where approval is meaningful."""


@dataclass
class ApprovalOutcome:
    work_item: WorkItem
    approval: Approval


def compute_content_hash(computation: Computation) -> str:
    """The fingerprint an approval binds to.

    Deliberately covers the *figures and their provenance*, not the row's metadata:
    re-running the same computation must not invalidate an approval, but different
    numbers or a different rule pack must.
    """
    payload = {
        "computation_id": str(computation.id),
        "result": computation.result,
        "result_hash": computation.result_hash,
        "inputs_hash": computation.inputs_hash,
        "pack_ref": computation.pack_ref,
        "engine_version": computation.engine_version,
    }
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


class WorkflowService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID, actor: Actor) -> None:
        self._s = session
        self._tenant_id = tenant_id
        self._actor = actor

    # --- creation & movement -------------------------------------------------

    async def create_work_item(
        self,
        *,
        entity_id: uuid.UUID,
        period_key: str,
        item_type: str,
        title: str,
        computation_id: uuid.UUID | None = None,
        prepared_by: str | None = None,
    ) -> WorkItem:
        uow = AuditedUnitOfWork(self._s, self._tenant_id, self._actor)
        item = WorkItem(
            tenant_id=self._tenant_id,
            entity_id=entity_id,
            period_key=period_key,
            item_type=item_type,
            title=title,
            computation_id=computation_id,
            state=WorkItemState.DRAFT,
            # When an agent creates the item, the human who requested the run owns
            # preparation — an agent cannot be a party to segregation of duties.
            prepared_by=prepared_by or self._actor.ref,
            created_by=self._actor.ref,
        )
        self._s.add(item)
        await self._s.flush()

        uow.record(
            "work_item.created",
            "work_item",
            str(item.id),
            after={"type": item_type, "period": period_key, "state": item.state},
        )
        uow.publish(
            "WorkItemCreated",
            {"work_item_id": str(item.id), "type": item_type, "entity_id": str(entity_id)},
        )
        await uow.commit()
        return item

    async def transition(
        self, work_item_id: uuid.UUID, to_state: str, *, comment: str | None = None
    ) -> WorkItem:
        item = await self._get_or_raise(work_item_id)
        assert_legal(item.state, to_state)

        uow = AuditedUnitOfWork(self._s, self._tenant_id, self._actor)
        from_state = item.state

        if to_state == WorkItemState.AWAITING_REVIEW:
            # Freeze what the reviewer will see, so "approve" can mean "approve this".
            item.content_hash = await self._current_content_hash(item)

        item.state = to_state
        self._s.add(
            WorkflowTransition(
                tenant_id=self._tenant_id,
                work_item_id=item.id,
                from_state=from_state,
                to_state=to_state,
                actor=self._actor.ref,
                comment=comment,
            )
        )
        uow.record(
            "work_item.transitioned",
            "work_item",
            str(item.id),
            before={"state": from_state},
            after={"state": to_state, "comment": comment},
        )
        uow.publish(
            "WorkItemTransitioned",
            {"work_item_id": str(item.id), "from": from_state, "to": to_state},
        )
        await uow.commit()
        return item

    # --- the gate ------------------------------------------------------------

    async def approve(
        self, work_item_id: uuid.UUID, *, content_hash: str, comment: str | None = None
    ) -> ApprovalOutcome:
        """Grant approval. Every guard here is a refusal a human can understand."""
        item = await self._get_or_raise(work_item_id)

        if item.state != WorkItemState.AWAITING_REVIEW:
            raise NotReviewableError(
                f"Work item is {item.state}; only items awaiting review can be approved"
            )

        if item.prepared_by == self._actor.ref:
            raise SegregationOfDutiesError(
                f"{self._actor.ref} prepared this item — a second reviewer must approve it"
            )

        current = await self._current_content_hash(item)
        if content_hash != current:
            raise StaleContentError(
                "The content changed since you opened this item. Refresh and re-review "
                "before approving."
            )

        uow = AuditedUnitOfWork(self._s, self._tenant_id, self._actor)
        approval = Approval(
            tenant_id=self._tenant_id,
            work_item_id=item.id,
            approver=self._actor.ref,
            content_hash=current,
            comment=comment,
        )
        self._s.add(approval)

        from_state = item.state
        item.state = WorkItemState.APPROVED
        self._s.add(
            WorkflowTransition(
                tenant_id=self._tenant_id,
                work_item_id=item.id,
                from_state=from_state,
                to_state=WorkItemState.APPROVED,
                actor=self._actor.ref,
                comment=comment,
            )
        )

        uow.record(
            "approval.granted",
            "work_item",
            str(item.id),
            before={"state": from_state},
            after={
                "state": WorkItemState.APPROVED,
                "approver": self._actor.ref,
                "content_hash": current,
                "comment": comment,
            },
        )
        uow.publish(
            "ApprovalGranted",
            {
                "work_item_id": str(item.id),
                "approver": self._actor.ref,
                "content_hash": current,
            },
        )
        await uow.commit()
        return ApprovalOutcome(work_item=item, approval=approval)

    async def attach_computation(
        self, work_item_id: uuid.UUID, computation_id: uuid.UUID
    ) -> WorkItem:
        """Point a work item at a (new) computation — the production path when data
        arrives late and the figures are recomputed.

        This is an audited operation rather than a quiet field update, because it is
        precisely what can invalidate an existing approval: the item now refers to
        different numbers than the ones a human signed off.
        """
        item = await self._get_or_raise(work_item_id)
        previous = item.computation_id

        uow = AuditedUnitOfWork(self._s, self._tenant_id, self._actor)
        item.computation_id = computation_id
        uow.record(
            "work_item.computation_attached",
            "work_item",
            str(item.id),
            before={"computation_id": str(previous) if previous else None},
            after={"computation_id": str(computation_id)},
        )
        await uow.commit()
        await self._s.refresh(item)
        return item

    async def revalidate(self, work_item_id: uuid.UUID) -> WorkItem:
        """Check an approved item against its current content and void if it has moved.

        Called when upstream data changes. The item returns to DRAFT and the approval is
        marked void with a reason — the history says "approved, then invalidated", which
        is a materially different fact from "never approved".
        """
        item = await self._get_or_raise(work_item_id)
        if item.state != WorkItemState.APPROVED:
            return item

        current = await self._current_content_hash(item)
        live_approval = await self._live_approval(item.id)
        if live_approval is None or live_approval.content_hash == current:
            return item

        uow = AuditedUnitOfWork(self._s, self._tenant_id, self._actor)
        live_approval.voided = True
        live_approval.voided_at = utcnow()
        live_approval.void_reason = "Underlying content changed after approval"

        item.state = WorkItemState.DRAFT
        item.content_hash = None
        self._s.add(
            WorkflowTransition(
                tenant_id=self._tenant_id,
                work_item_id=item.id,
                from_state=WorkItemState.APPROVED,
                to_state=WorkItemState.DRAFT,
                actor=self._actor.ref,
                comment="Approval voided: content changed",
            )
        )
        uow.record(
            "approval.voided",
            "work_item",
            str(item.id),
            before={"state": WorkItemState.APPROVED, "content_hash": live_approval.content_hash},
            after={"state": WorkItemState.DRAFT, "current_hash": current},
        )
        uow.publish(
            "ApprovalVoided",
            {"work_item_id": str(item.id), "reason": "content_changed"},
        )
        await uow.commit()
        return item

    # --- reads ---------------------------------------------------------------

    async def get(self, work_item_id: uuid.UUID) -> WorkItem | None:
        return (
            await self._s.execute(select(WorkItem).where(WorkItem.id == work_item_id))
        ).scalar_one_or_none()

    async def list_items(self, *, state: str | None = None) -> list[WorkItem]:
        stmt = select(WorkItem).order_by(WorkItem.created_at.desc())
        if state:
            stmt = stmt.where(WorkItem.state == state)
        return list((await self._s.execute(stmt)).scalars().all())

    async def history(self, work_item_id: uuid.UUID) -> list[WorkflowTransition]:
        result = await self._s.execute(
            select(WorkflowTransition)
            .where(WorkflowTransition.work_item_id == work_item_id)
            .order_by(WorkflowTransition.occurred_at)
        )
        return list(result.scalars().all())

    async def approvals(self, work_item_id: uuid.UUID) -> list[Approval]:
        result = await self._s.execute(
            select(Approval)
            .where(Approval.work_item_id == work_item_id)
            .order_by(Approval.granted_at)
        )
        return list(result.scalars().all())

    async def can_approve(self, work_item_id: uuid.UUID) -> tuple[bool, str | None]:
        """Why the button is disabled — the UI shows this reason rather than a dead control."""
        item = await self.get(work_item_id)
        if item is None:
            return False, "Work item not found"
        if item.state != WorkItemState.AWAITING_REVIEW:
            return False, f"Item is {item.state}, not awaiting review"
        if item.prepared_by == self._actor.ref:
            return False, "You prepared this item — a second reviewer is required"
        return True, None

    # --- internals -----------------------------------------------------------

    async def _get_or_raise(self, work_item_id: uuid.UUID) -> WorkItem:
        item = await self.get(work_item_id)
        if item is None:
            raise NotReviewableError(f"Work item {work_item_id} not found")
        return item

    async def _live_approval(self, work_item_id: uuid.UUID) -> Approval | None:
        result = await self._s.execute(
            select(Approval)
            .where(Approval.work_item_id == work_item_id, Approval.voided.is_(False))
            .order_by(Approval.granted_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _current_content_hash(self, item: WorkItem) -> str:
        if item.computation_id is None:
            return hashlib.sha256(f"work_item:{item.id}".encode()).hexdigest()
        computation = (
            await self._s.execute(select(Computation).where(Computation.id == item.computation_id))
        ).scalar_one()
        return compute_content_hash(computation)
