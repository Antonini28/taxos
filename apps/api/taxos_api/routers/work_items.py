"""Work item and approval endpoints (US-402)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from taxos_contracts.workflow import (
    ApprovalEligibility,
    ApprovalOut,
    ApprovalRequest,
    CreateWorkItemRequest,
    TransitionOut,
    TransitionRequest,
    WorkItemOut,
)
from taxos_core.workflow.service import (
    NotReviewableError,
    SegregationOfDutiesError,
    StaleContentError,
    WorkflowService,
)
from taxos_core.workflow.states import TransitionError

from taxos_api.deps import Principal, current_principal, db_session
from taxos_api.errors import ConflictError, NotFoundError, PermissionDeniedError, ValidationFailed

router = APIRouter(prefix="/work-items", tags=["workflow"])

PrincipalDep = Annotated[Principal, Depends(current_principal)]
SessionDep = Annotated[AsyncSession, Depends(db_session)]


def _service(session: AsyncSession, principal: Principal) -> WorkflowService:
    return WorkflowService(session, principal.tenant_id, principal.actor)


@router.post("", response_model=WorkItemOut, status_code=status.HTTP_201_CREATED)
async def create_work_item(
    body: CreateWorkItemRequest, principal: PrincipalDep, session: SessionDep
) -> WorkItemOut:
    item = await _service(session, principal).create_work_item(
        entity_id=body.entity_id,
        period_key=body.period_key,
        item_type=body.item_type,
        title=body.title,
        computation_id=body.computation_id,
    )
    return WorkItemOut.model_validate(item, from_attributes=True)


@router.get("", response_model=list[WorkItemOut])
async def list_work_items(
    principal: PrincipalDep, session: SessionDep, state: str | None = None
) -> list[WorkItemOut]:
    items = await _service(session, principal).list_items(state=state)
    return [WorkItemOut.model_validate(i, from_attributes=True) for i in items]


@router.get("/{work_item_id}", response_model=WorkItemOut)
async def get_work_item(
    work_item_id: uuid.UUID, principal: PrincipalDep, session: SessionDep
) -> WorkItemOut:
    item = await _service(session, principal).get(work_item_id)
    if item is None:
        raise NotFoundError(f"Work item {work_item_id} not found")
    return WorkItemOut.model_validate(item, from_attributes=True)


@router.post("/{work_item_id}/transitions", response_model=WorkItemOut)
async def transition(
    work_item_id: uuid.UUID,
    body: TransitionRequest,
    principal: PrincipalDep,
    session: SessionDep,
) -> WorkItemOut:
    service = _service(session, principal)
    try:
        item = await service.transition(work_item_id, body.to_state, comment=body.comment)
    except TransitionError as exc:
        # 409: the request was well-formed but the item is not in a state that permits it.
        raise ConflictError(str(exc)) from exc
    except NotReviewableError as exc:
        raise NotFoundError(str(exc)) from exc
    return WorkItemOut.model_validate(item, from_attributes=True)


@router.get("/{work_item_id}/approval-eligibility", response_model=ApprovalEligibility)
async def approval_eligibility(
    work_item_id: uuid.UUID, principal: PrincipalDep, session: SessionDep
) -> ApprovalEligibility:
    """Lets the UI state *why* approval is unavailable, rather than presenting a
    disabled control with no explanation."""
    service = _service(session, principal)
    item = await service.get(work_item_id)
    if item is None:
        raise NotFoundError(f"Work item {work_item_id} not found")
    allowed, reason = await service.can_approve(work_item_id)
    return ApprovalEligibility(can_approve=allowed, reason=reason, content_hash=item.content_hash)


@router.post("/{work_item_id}/approvals", response_model=ApprovalOut, status_code=201)
async def approve(
    work_item_id: uuid.UUID,
    body: ApprovalRequest,
    principal: PrincipalDep,
    session: SessionDep,
) -> ApprovalOut:
    service = _service(session, principal)
    try:
        outcome = await service.approve(
            work_item_id, content_hash=body.content_hash, comment=body.comment
        )
    except SegregationOfDutiesError as exc:
        raise PermissionDeniedError(str(exc)) from exc
    except StaleContentError as exc:
        raise ConflictError(str(exc)) from exc
    except NotReviewableError as exc:
        raise ValidationFailed(str(exc)) from exc
    return ApprovalOut.model_validate(outcome.approval, from_attributes=True)


@router.get("/{work_item_id}/approvals", response_model=list[ApprovalOut])
async def list_approvals(
    work_item_id: uuid.UUID, principal: PrincipalDep, session: SessionDep
) -> list[ApprovalOut]:
    approvals = await _service(session, principal).approvals(work_item_id)
    return [ApprovalOut.model_validate(a, from_attributes=True) for a in approvals]


@router.get("/{work_item_id}/history", response_model=list[TransitionOut])
async def history(
    work_item_id: uuid.UUID, principal: PrincipalDep, session: SessionDep
) -> list[TransitionOut]:
    transitions = await _service(session, principal).history(work_item_id)
    return [TransitionOut.model_validate(t, from_attributes=True) for t in transitions]
