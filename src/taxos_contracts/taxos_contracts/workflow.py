"""Workflow API contracts.

The approval request carries the content hash the reviewer saw — the client cannot
approve "whatever is current", only "what I read". That is the wire-level expression
of GP-1.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CreateWorkItemRequest(BaseModel):
    entity_id: uuid.UUID
    period_key: str = Field(pattern=r"^\d{4}-Q[1-4]$")
    item_type: str = "VAT_RETURN"
    title: str
    computation_id: uuid.UUID | None = None


class TransitionRequest(BaseModel):
    to_state: str
    comment: str | None = None


class ApprovalRequest(BaseModel):
    content_hash: str = Field(min_length=64, max_length=64)
    comment: str | None = None


class ApprovalOut(BaseModel):
    id: uuid.UUID
    approver: str
    content_hash: str
    comment: str | None
    granted_at: datetime
    voided: bool
    void_reason: str | None


class TransitionOut(BaseModel):
    from_state: str
    to_state: str
    actor: str
    comment: str | None
    occurred_at: datetime


class WorkItemOut(BaseModel):
    id: uuid.UUID
    entity_id: uuid.UUID
    period_key: str
    item_type: str
    title: str
    state: str
    prepared_by: str
    computation_id: uuid.UUID | None
    content_hash: str | None
    created_at: datetime


class ApprovalEligibility(BaseModel):
    """Why the approve button is enabled or not — the UI explains rather than greys out."""

    can_approve: bool
    reason: str | None = None
    content_hash: str | None = None
