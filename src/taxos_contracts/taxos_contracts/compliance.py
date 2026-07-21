"""Computation API contracts.

Box values are decimal strings and lineage entries carry their citation — the wire
format makes "show me why" a first-class response, not an afterthought.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ComputeRequest(BaseModel):
    entity_id: uuid.UUID
    period_key: str = Field(pattern=r"^\d{4}-Q[1-4]$", examples=["2026-Q2"])
    pack_version: str = "1.0.0"


class BoxOut(BaseModel):
    box_id: str
    label: str
    value: str = Field(description="Decimal as string — never a float")
    derived: bool


class ComputationOut(BaseModel):
    id: uuid.UUID
    entity_id: uuid.UUID
    period_key: str
    tax_type: str
    pack_ref: str
    engine_version: str
    inputs_hash: str
    result_hash: str
    unmapped_codes: list[str]
    boxes: list[BoxOut]
    computed_at: datetime


class LineageEntryOut(BaseModel):
    row_id: uuid.UUID
    document_ref: str
    counterparty: str
    kind: str
    amount: str
    vat_code: str
    citation_ref: str


class LineageOut(BaseModel):
    computation_id: uuid.UUID
    box_id: str
    box_value: str
    contribution_total: str = Field(
        description="Must equal box_value exactly — the reconciliation is the point"
    )
    entries: list[LineageEntryOut]
