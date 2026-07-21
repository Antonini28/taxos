"""The work-item state machine (US-402, GP-1).

Legal transitions are declared here as data, so the set of things that can happen to a
work item is readable in one place — by a developer, a reviewer, or an auditor. The
absence of an edge is the enforcement: there is no transition from any state to
APPROVED that does not pass through the approval gate.
"""

from dataclasses import dataclass


class WorkItemState:
    DRAFT = "DRAFT"
    AWAITING_REVIEW = "AWAITING_REVIEW"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    APPROVED = "APPROVED"
    CANCELLED = "CANCELLED"


# Transitions an actor may request directly. APPROVED is deliberately absent as a
# target here: it is reachable only through ApprovalService.grant(), which enforces
# segregation of duties and content-hash binding.
LEGAL_TRANSITIONS: dict[str, set[str]] = {
    WorkItemState.DRAFT: {WorkItemState.AWAITING_REVIEW, WorkItemState.CANCELLED},
    WorkItemState.AWAITING_REVIEW: {
        WorkItemState.CHANGES_REQUESTED,
        WorkItemState.DRAFT,  # inputs changed — approval void, back to preparation
        WorkItemState.CANCELLED,
    },
    WorkItemState.CHANGES_REQUESTED: {WorkItemState.AWAITING_REVIEW, WorkItemState.CANCELLED},
    WorkItemState.APPROVED: {
        # An approved item can only be re-opened by invalidation (inputs changed),
        # which the system does — a human cannot simply un-approve.
        WorkItemState.DRAFT,
    },
    WorkItemState.CANCELLED: set(),
}

TERMINAL_STATES = {WorkItemState.APPROVED, WorkItemState.CANCELLED}


@dataclass(frozen=True)
class TransitionError(Exception):
    """Raised when a transition is not on the map. The message names both states so the
    UI can explain the refusal rather than merely reporting failure."""

    from_state: str
    to_state: str

    def __str__(self) -> str:
        allowed = ", ".join(sorted(LEGAL_TRANSITIONS.get(self.from_state, set()))) or "none"
        return (
            f"Cannot move work item from {self.from_state} to {self.to_state}. "
            f"Allowed from {self.from_state}: {allowed}"
        )


def assert_legal(from_state: str, to_state: str) -> None:
    if to_state not in LEGAL_TRANSITIONS.get(from_state, set()):
        raise TransitionError(from_state, to_state)
