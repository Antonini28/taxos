"""Compliance: the deterministic computation core (AP-2, ADR-005).

The engine is a pure function over (transactions, pack, params). No I/O, no LLM, no
floats — and identical inputs always produce byte-identical output. Everything that
makes a figure defensible lives here.
"""
