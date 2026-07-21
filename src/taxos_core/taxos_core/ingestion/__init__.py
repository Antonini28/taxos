"""Ingestion: batches, validation, quarantine (US-201, FR-101/102).

Invariant this module owns: no unvalidated row reaches a computation. Failures are
quarantined with rule-level reasons — never silently dropped, never auto-corrected.
"""
