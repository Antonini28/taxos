"""TaxOS shared contracts.

Rule (Phase 6, doc 01): this package depends on pydantic ONLY. It is consumed by
every service and by frontend type generation — anything heavier creates coupling
the architecture forbids.
"""

from taxos_contracts.problem import Problem

__all__ = ["Problem"]
