"""Deterministic demo seed (Phase 6 doc 07 §2).

Fixed UUIDs so the frontend, tests, and demo script can all refer to the same entities
without a lookup dance. Every seeded finding is documented in FINDINGS.md — demos should
never fish for something interesting.

Usage:  uv run python tools/seed/seed.py [--reset]
"""

import asyncio
import sys
import uuid

from sqlalchemy import text
from taxos_core.ingestion.service import IngestionService
from taxos_core.masterdata.service import EntityService
from taxos_core.shared.persistence.session import tenant_session
from taxos_core.shared.persistence.uow import Actor

TENANT_ID = uuid.UUID("00000000-0000-0000-0000-0000000000d1")
ENTITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000e01")
PREPARER = Actor.user("daniel@dev")

SALES_CSV = (
    b"document_ref,document_date,counterparty,net_amount,vat_amount,vat_code,currency\n"
    b"SI-2601,2026-04-08,Northwind Retail Group,42500.00,8500.00,S20,GBP\n"
    b"SI-2602,2026-04-22,Cobalt Media Ltd,18000.00,3600.00,S20,GBP\n"
    b"SI-2603,2026-05-06,Harborview Logistics,27750.00,5550.00,S20,GBP\n"
    b"SI-2604,2026-05-19,St Aiden's Health Trust,31000.00,0.00,E00,GBP\n"
    b"SI-2605,2026-06-03,Lyra Publishing,9400.00,0.00,Z00,GBP\n"
    b"SI-2606,2026-06-24,Northwind Retail Group,36200.00,7240.00,S20,GBP\n"
)

# Seeded findings in this file — see FINDINGS.md:
#   PI-2607 carries an unrecognised VAT code (ING-005, quarantined at ingestion)
#   PI-2609 dates outside the quarter (ING-003, quarantined at ingestion)
#   PI-2605 duplicates PI-2601 exactly (DUP-001, HIGH — same supplier, same £12,400)
#   PI-2602 is an exact round £48,000 (RND-001, LOW)
PURCHASES_CSV = (
    b"document_ref,document_date,counterparty,net_amount,vat_amount,vat_code,currency\n"
    b"PI-2601,2026-04-11,Apex Supplies Ltd,12400.00,2480.00,S20,GBP\n"
    b"PI-2602,2026-04-15,Delta Construction Ltd,48000.00,0.00,RC20,GBP\n"
    b"PI-2603,2026-04-29,Orchard Facilities,3250.00,650.00,S20,GBP\n"
    b"PI-2604,2026-05-12,Kestrel IT Services,8800.00,1760.00,S20,GBP\n"
    b"PI-2605,2026-05-27,Apex Supplies Ltd,12400.00,2480.00,S20,GBP\n"  # duplicates PI-2601
    b"PI-2606,2026-06-09,Meridian Utilities,2100.00,105.00,R05,GBP\n"
    b"PI-2607,2026-06-15,Vantage Consulting,7500.00,1500.00,XX9,GBP\n"
    b"PI-2608,2026-06-18,Delta Construction Ltd,22000.00,0.00,RC20,GBP\n"
    b"PI-2609,2026-01-14,Apex Supplies Ltd,4300.00,860.00,S20,GBP\n"
)

TABLES_TO_CLEAR = [
    "anomaly",
    "anomaly_scan",
    "agent_step",
    "agent_run",
    "approval",
    "workflow_transition",
    "work_item",
    "computation_line_source",
    "computation_line",
    "computation",
    "validation_result",
    "quarantine_row",
    "transaction_row",
    "batch",
    "audit_event",
    "outbox_event",
]


async def _truncate_all() -> None:
    """Clear transactional data as the owner role, using TRUNCATE.

    DELETE is refused here — agent_step, workflow_transition and the audit log carry
    append-only triggers, and they fire per row. That the demo's own reset has to work
    around the immutability guarantee is a reasonable sign the guarantee is real.
    TRUNCATE does not fire row triggers, and requires owner privileges the app role
    deliberately lacks.
    """
    from sqlalchemy.ext.asyncio import create_async_engine
    from taxos_core.shared.config import Settings

    engine = create_async_engine(Settings().database.migration_dsn.get_secret_value())
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(f"TRUNCATE {', '.join(TABLES_TO_CLEAR)} RESTART IDENTITY CASCADE")
            )
    finally:
        await engine.dispose()


async def seed(reset: bool = False) -> None:
    async with tenant_session(TENANT_ID) as session:
        await session.execute(
            text(
                "INSERT INTO tenant (id, name, slug, created_by) "
                "VALUES (:id, 'Meridian Group', 'meridian', 'system:seed') "
                "ON CONFLICT (id) DO NOTHING"
            ),
            {"id": TENANT_ID},
        )
        await session.commit()

    async with tenant_session(TENANT_ID) as session:
        if reset:
            await _truncate_all()
            print("cleared transactional data")

        entities = await EntityService(session, TENANT_ID, PREPARER).list_entities()
        if not any(e.id == ENTITY_ID for e in entities):
            await session.execute(
                text(
                    "INSERT INTO legal_entity "
                    "(id, tenant_id, code, name, jurisdiction_code, created_by) "
                    "VALUES (:id, :t, 'UK-01', 'Meridian UK Limited', 'UK', 'system:seed')"
                ),
                {"id": ENTITY_ID, "t": TENANT_ID},
            )
            await session.commit()
            print(f"created entity UK-01 ({ENTITY_ID})")

    async with tenant_session(TENANT_ID) as session:
        ingestion = IngestionService(session, TENANT_ID, PREPARER)
        for filename, content, source in (
            ("sales_q2_2026.csv", SALES_CSV, "AR"),
            ("purchases_q2_2026.csv", PURCHASES_CSV, "AP"),
        ):
            try:
                report = await ingestion.ingest_csv(
                    entity_id=ENTITY_ID,
                    period_key="2026-Q2",
                    source_type=source,
                    filename=filename,
                    content=content,
                )
                print(
                    f"ingested {filename}: {report.accepted_count} accepted, "
                    f"{report.quarantined_count} quarantined {report.rule_breakdown or ''}"
                )
            except Exception as exc:  # noqa: BLE001 — seeding is idempotent by intent
                print(f"skipped {filename}: {exc}")

    print(f"\ntenant {TENANT_ID}\nentity {ENTITY_ID}")


if __name__ == "__main__":
    asyncio.run(seed(reset="--reset" in sys.argv))
