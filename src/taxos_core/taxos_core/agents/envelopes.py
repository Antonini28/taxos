"""The envelope contract (docs/ai/02 §2).

Supervisor and specialists exchange typed envelopes, never free conversation. This is
what makes every hop traceable, budgetable, and framework-portable: swapping the
orchestration library later changes the runtime, not this contract.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal

ConfidenceBasis = Literal["DETERMINISTIC", "GROUNDED", "MODEL_JUDGEMENT"]
StepStatus = Literal["COMPLETED", "ESCALATED", "FAILED"]


@dataclass(frozen=True)
class TaskEnvelope:
    """What the Supervisor asks of a specialist.

    Context travels as *references*, never as resolved data: the specialist fetches
    what it needs under its own tool grants, so the Supervisor cannot hand an agent
    data it is not entitled to see.
    """

    agent: str
    goal: str
    context_refs: dict[str, str] = field(default_factory=dict)
    budget_tool_calls: int = 6


@dataclass
class Escalation:
    """Why a run stopped and what would unblock it. Named gaps only — an escalation
    that says "something went wrong" is a dead end for the human receiving it."""

    reason: str
    needed_input: str
    suggested_owner: str = "preparer"


@dataclass
class ResultEnvelope:
    """What a specialist returns. Confidence always carries its basis."""

    agent: str
    status: StepStatus
    output: dict[str, Any] = field(default_factory=dict)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    confidence: Decimal = Decimal("1.0")
    confidence_basis: ConfidenceBasis = "DETERMINISTIC"
    escalation: Escalation | None = None
    model: str = "stub"
    cost_gbp: Decimal = Decimal("0")
    duration_ms: int = 0
