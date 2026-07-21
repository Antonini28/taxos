"""RFC 9457 problem details — the error shape of every TaxOS API response (Phase 2 doc 06 §3)."""

from pydantic import BaseModel, Field


class FieldError(BaseModel):
    field: str
    message: str


class Problem(BaseModel):
    """application/problem+json body. `trace_id` links the response to its distributed trace."""

    type: str = Field(default="about:blank")
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None
    trace_id: str | None = None
    errors: list[FieldError] | None = None
