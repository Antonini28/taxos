"""Ingestion API contracts. Money crosses the wire as a decimal string, never a float."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class BatchAccepted(BaseModel):
    """202 response — validation is asynchronous in shape even while synchronous in fact."""

    batch_id: uuid.UUID
    status: str
    filename: str


class RuleFailure(BaseModel):
    rule: str
    message: str
    field: str | None = None


class QuarantinedRow(BaseModel):
    row_number: int
    failures: list[RuleFailure]
    source_payload: dict


class ValidationReportOut(BaseModel):
    batch_id: uuid.UUID
    status: str
    row_count: int
    accepted_count: int
    quarantined_count: int
    control_total: str = Field(description="Decimal as string — never a float")
    rule_breakdown: dict[str, int]


class BatchOut(BaseModel):
    id: uuid.UUID
    entity_id: uuid.UUID
    period_key: str
    source_type: str
    filename: str
    status: str
    row_count: int
    accepted_count: int
    quarantined_count: int
    created_at: datetime
