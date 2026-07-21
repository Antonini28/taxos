"""Reporting: read models for dashboards (FR-601).

Nothing here mutates. Aggregates are computed live at this scale; the `rpt_*` projection
tables described in the architecture become worthwhile when query cost demands them, and
this module's interface is what they would sit behind.
"""
