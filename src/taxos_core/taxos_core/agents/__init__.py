"""Agent run records (FR-302).

The runtime itself lives in `taxos_agents` — isolated, with no direct database access
(ADR-012). These tables are the *evidence* of what agents did, owned by the core and
written through the same audited path as everything else. A run that cannot be traced
cannot proceed.
"""
