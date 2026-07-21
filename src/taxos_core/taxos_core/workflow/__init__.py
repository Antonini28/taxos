"""Workflow: work items, the state machine, and the human approval gate.

This module owns GP-1. Agents prepare; humans approve. The gate is not a policy
document — it is a state machine that refuses illegal transitions, a segregation-of-duties
check that cannot be argued with, and an approval bound to a hash of exactly what was
reviewed.
"""
