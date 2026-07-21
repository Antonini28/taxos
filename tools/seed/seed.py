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

# Two seeded findings live in this file — see FINDINGS.md:
#   PI-2607 carries an unrecognised VAT code (ING-005)
#   PI-2609 dates outside the quarter (ING-003)
PURCHASES_CSV = (
    b"document_ref,document_date,counterparty,net_amount,vat_amount,vat_code,currency\n"
    b"PI-2601,2026-04-11,Apex Supplies Ltd,12400.00,2480.00,S20,GBP\n"
    b"PI-2602,2026-04-15,Delta Construction Ltd,48000.00,0.00,RC20,GBP\n"
    b"PI-2603,2026-04-29,Orchard Facilities,3250.00,650.00,S20,GBP\n"
    b"PI-2604,2026-05-12,Kestrel IT Services,8800.00,1760.00,S20,GBP\n"
    b"PI-2605,2026-05-27,Apex Supplies Ltd,15600.00,3120.00,S20,GBP\n"
    b"PI-2606,2026-06-09,Meridian Utilities,2100.00,105.00,R05,GBP\n"
    b"PI-2607,2026-06-15,Vantage Consulting,7500.00,1500.00,XX9,GBP\n"
    b"PI-2608,2026-06-18,Delta Construction Ltd,22000.00,0.00,RC20,GBP\n"
    b"PI-2609,2026-01-14,Apex Supplies Ltd,4300.00,860.00,S20,GBP\n"
)

TABLES_TO_CLEAR = [
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
]


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
            for table in TABLES_TO_CLEAR:
                # Table names come from the constant above, never from input — the
                # f-string is safe here and the linter is told so explicitly.
                await session.execute(
                    text(f"DELETE FROM {table} WHERE tenant_id = :t"),  # noqa: S608
                    {"t": TENANT_ID},
                )
            await session.commit()
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
