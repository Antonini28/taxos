"""The demo: one command from empty to a platform worth showing.

Runs the full R1 slice against a clean database so a walkthrough never begins with
"let me just set this up". Every seeded finding is intentional and listed in FINDINGS.md
— a demo that has to fish for something interesting is a demo that will fail live.

Usage:  just demo        (or: uv run python tools/seed/demo.py)
"""

import asyncio
import sys
from pathlib import Path

# Windows consoles default to cp1252; the status glyphs below need UTF-8. Without this the
# demo — the first thing anyone runs — crashes on its own first print line.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Run this file directly or as a module — both should work for a demo command.
sys.path.insert(0, str(Path(__file__).parent))

from seed import ENTITY_ID, TENANT_ID, seed  # sibling module (see sys.path below)
from taxos_core.agents.supervisor import Supervisor
from taxos_core.shared.persistence.session import tenant_session
from taxos_core.shared.persistence.uow import Actor
from taxos_core.workflow.service import WorkflowService

PREPARER = Actor.user("daniel@dev")
REVIEWER = Actor.user("priya@dev")

STEP = "\n\033[1m▸ {}\033[0m"
OK = "  \033[32m✓\033[0m {}"
NOTE = "  \033[2m{}\033[0m"


async def run_demo(*, approve: bool = False) -> None:
    print(STEP.format("Seeding Meridian Group"))
    await seed(reset=True)

    print(STEP.format("Running the agent VAT cycle"))
    async with tenant_session(TENANT_ID) as session:
        supervisor = Supervisor(session, TENANT_ID, PREPARER)
        run = await supervisor.start_vat_run(entity_id=ENTITY_ID, period_key="2026-Q2")
        outcome = await supervisor.execute(run.id)

        for step in outcome.steps:
            narrative = step.output.get("narrative", "")
            print(OK.format(f"{step.agent}: {narrative}"))
            for observation in step.output.get("observations", []):
                print(NOTE.format(observation))

        print(OK.format(f"run ended in {outcome.run.state}"))
        work_item_id = outcome.run.work_item_id

    print(STEP.format("Running the agent Corporation Tax cycle"))
    async with tenant_session(TENANT_ID) as session:
        supervisor = Supervisor(session, TENANT_ID, PREPARER)
        ct_run = await supervisor.start_corporation_tax_run(entity_id=ENTITY_ID, period_key="2026")
        ct_outcome = await supervisor.execute(ct_run.id)
        for step in ct_outcome.steps:
            print(OK.format(f"{step.agent}: {step.output.get('narrative', '')}"))
        print(OK.format(f"CT run ended in {ct_outcome.run.state} — same engine, a different pack"))

    print(STEP.format("Scanning for anomalies"))
    async with tenant_session(TENANT_ID) as session:
        from taxos_core.risk.service import RiskService

        scan = await RiskService(session, TENANT_ID, PREPARER).scan(
            entity_id=ENTITY_ID, period_key="2026-Q2"
        )
        print(OK.format(f"{scan.flagged} flagged of {scan.rows_scanned} transactions"))

    if work_item_id is None:
        print("\n  Run parked — nothing to review. Check the escalation in the workspace.")
        return

    # Demonstrate the gate rather than describing it: the preparer is refused, by name.
    print(STEP.format("Attempting approval as the preparer"))
    async with tenant_session(TENANT_ID) as session:
        workflow = WorkflowService(session, TENANT_ID, PREPARER)
        allowed, reason = await workflow.can_approve(work_item_id)
        print(OK.format(f"refused — {reason}") if not allowed else "  unexpectedly allowed")

    if approve:
        print(STEP.format("Approving as the reviewer"))
        async with tenant_session(TENANT_ID) as session:
            workflow = WorkflowService(session, TENANT_ID, REVIEWER)
            item = await workflow.get(work_item_id)
            result = await workflow.approve(
                item.id,
                content_hash=item.content_hash,
                comment="Lineage checked on Box 4; reverse charge traced to VATDSAG.",
            )
            print(OK.format(f"approved by {result.approval.approver}"))
            print(NOTE.format(f"bound to content hash {result.approval.content_hash[:16]}…"))

    print(STEP.format("Verifying the audit chain"))
    async with tenant_session(TENANT_ID) as session:
        from taxos_core.audit.verify import verify_chain

        chain = await verify_chain(session, TENANT_ID)
        print(
            OK.format(
                f"{chain.events_checked} events rehashed and matched"
                if chain.verified
                else f"CHAIN BROKEN at seq {chain.broken_at_seq}"
            )
        )

    print(
        "\n\033[1mReady.\033[0m Open http://localhost:3000\n"
        "  Ingestion  — 2 quarantined rows with their rule reasons\n"
        "  VAT        — 9 boxes, each drilling to invoices and HMRC citations\n"
        "  Agents     — the run above, step by step\n"
        "  Fraud      — the seeded duplicate (PI-2605 = PI-2601), reason-coded disposition\n"
        "  Approvals  — the gate; switch seats to approve, then export the evidence pack\n"
        "  Audit      — the chain, verifiable on demand\n"
    )


if __name__ == "__main__":
    asyncio.run(run_demo(approve="--approve" in sys.argv))
