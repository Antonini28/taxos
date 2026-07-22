"""US-801: anomaly detection and the disposition loop.

The detectors are tested as pure functions (no database), the service against real
Postgres. The disposition-as-label discipline gets its own test, because "the reason
matters" is a claim the ML story rests on.
"""

from decimal import Decimal

import pytest
from sqlalchemy import select
from taxos_core.ingestion.service import IngestionService
from taxos_core.masterdata.service import EntityService
from taxos_core.risk.detectors import Transaction, detect_all, detect_duplicates
from taxos_core.risk.models import Anomaly, AnomalyStatus
from taxos_core.risk.service import InvalidDispositionError, RiskService
from taxos_core.shared.persistence.uow import Actor

REVIEWER = Actor.user("priya@dev")

# Two seeded findings: PI-D1 and PI-D2 are an exact duplicate pair; PI-BIG is a round amount.
RISK_CSV = (
    b"document_ref,document_date,counterparty,net_amount,vat_amount,vat_code,currency\n"
    b"PI-D1,2026-04-10,Apex Supplies Ltd,8400.00,1680.00,S20,GBP\n"
    b"PI-D2,2026-04-24,Apex Supplies Ltd,8400.00,1680.00,S20,GBP\n"
    b"PI-BIG,2026-05-02,Delta Construction Ltd,25000.00,5000.00,S20,GBP\n"
    b"PI-OK,2026-05-14,Orchard Facilities,3271.55,654.31,S20,GBP\n"
)


def _txn(ref, cp, amount):
    return Transaction(
        row_id=ref,
        document_ref=ref,
        counterparty=cp,
        net_amount=Decimal(amount),
        vat_amount=Decimal("0"),
        vat_code="S20",
    )


# --- detectors (pure) ---------------------------------------------------------


def test_exact_duplicate_is_flagged_high():
    findings = detect_duplicates(
        [
            _txn("A", "Apex", "8400.00"),
            _txn("B", "Apex", "8400.00"),
        ]
    )
    assert len(findings) == 1
    assert findings[0].severity == "HIGH"
    assert findings[0].anomaly_type == "POSSIBLE_DUPLICATE"
    assert "A" in findings[0].explanation  # names the twin


def test_near_duplicate_within_tolerance_is_medium():
    findings = detect_duplicates(
        [
            _txn("A", "Apex", "10000.00"),
            _txn("B", "Apex", "10150.00"),  # +1.5%
        ]
    )
    assert len(findings) == 1 and findings[0].severity == "MEDIUM"


def test_different_counterparties_are_not_duplicates():
    findings = detect_duplicates(
        [
            _txn("A", "Apex", "8400.00"),
            _txn("B", "Borough", "8400.00"),
        ]
    )
    assert findings == []


def test_round_amount_flagged_low():
    findings = detect_all([_txn("A", "Delta", "25000.00")])
    round_findings = [f for f in findings if f.anomaly_type == "ROUND_AMOUNT"]
    assert len(round_findings) == 1 and round_findings[0].severity == "LOW"


def test_every_finding_carries_an_explanation():
    findings = detect_all(
        [
            _txn("A", "Apex", "8400.00"),
            _txn("B", "Apex", "8400.00"),
            _txn("C", "Delta", "25000.00"),
        ]
    )
    assert findings
    assert all(f.explanation and f.evidence for f in findings)


# --- service (real Postgres) --------------------------------------------------


@pytest.fixture
async def scanned(session_a, tenant_a):
    entity = await EntityService(session_a, tenant_a, REVIEWER).create_entity(
        code="UK-01", name="Meridian UK Ltd", jurisdiction_code="UK"
    )
    await IngestionService(session_a, tenant_a, REVIEWER).ingest_csv(
        entity_id=entity.id,
        period_key="2026-Q2",
        source_type="AP",
        filename="ap.csv",
        content=RISK_CSV,
    )
    result = await RiskService(session_a, tenant_a, REVIEWER).scan(
        entity_id=entity.id, period_key="2026-Q2"
    )
    return entity.id, result


async def test_scan_persists_anomalies_with_severity_order(session_a, tenant_a, scanned):
    _, result = scanned
    assert result.new_anomalies >= 2  # duplicate + round amount

    anomalies = await RiskService(session_a, tenant_a, REVIEWER).list_anomalies()
    severities = [a.severity for a in anomalies]
    # HIGH before LOW — the queue is ordered by what to look at first.
    assert severities.index("HIGH") < severities.index("LOW")


async def test_rescanning_does_not_duplicate_anomalies(session_a, tenant_a, scanned):
    entity_id, _ = scanned
    service = RiskService(session_a, tenant_a, REVIEWER)
    before = len(await service.list_anomalies())
    again = await service.scan(entity_id=entity_id, period_key="2026-Q2")
    after = len(await service.list_anomalies())
    assert again.new_anomalies == 0
    assert before == after


async def test_disposition_records_a_reason_coded_label(session_a, tenant_a, scanned):
    service = RiskService(session_a, tenant_a, REVIEWER)
    anomalies = await service.list_anomalies(status=AnomalyStatus.OPEN)
    duplicate = next(a for a in anomalies if a.anomaly_type == "POSSIBLE_DUPLICATE")

    updated = await service.disposition(
        duplicate.id, confirm=True, reason="GENUINE_DUPLICATE", note="Same PO, paid twice."
    )
    assert updated.status == AnomalyStatus.CONFIRMED
    assert updated.disposition_reason == "GENUINE_DUPLICATE"
    assert updated.dispositioned_by == "user:priya@dev"
    assert updated.dispositioned_at is not None


async def test_dismiss_reason_distinguishes_true_negative_from_censored(
    session_a, tenant_a, scanned
):
    """The label taxonomy's whole point: NO_TIME is not the same signal as RECURRING_CONTRACT."""
    from taxos_core.risk.models import DISMISS_REASONS

    assert "true negative" in DISMISS_REASONS["RECURRING_CONTRACT"]
    assert "censored" in DISMISS_REASONS["NO_TIME"]


async def test_invalid_disposition_reason_is_refused(session_a, tenant_a, scanned):
    service = RiskService(session_a, tenant_a, REVIEWER)
    anomaly = (await service.list_anomalies())[0]
    with pytest.raises(InvalidDispositionError, match="not a valid"):
        await service.disposition(anomaly.id, confirm=True, reason="MADE_UP_REASON")


async def test_scan_and_disposition_are_audited(session_a, tenant_a, scanned):
    from taxos_core.audit.models import AuditEvent
    from taxos_core.audit.verify import verify_chain

    service = RiskService(session_a, tenant_a, REVIEWER)
    anomaly = (await service.list_anomalies())[0]
    await service.disposition(anomaly.id, confirm=False, reason="REVIEWED_ACCEPTABLE")

    actions = {a.action for a in (await session_a.execute(select(AuditEvent))).scalars().all()}
    assert {"anomaly_scan.completed", "anomaly.dispositioned"} <= actions
    assert (await verify_chain(session_a, tenant_a)).verified is True


async def test_anomalies_are_tenant_isolated(session_a, session_b, tenant_a, scanned):
    assert (await session_b.execute(select(Anomaly))).scalars().all() == []


# --- Rung 2: the model runs beside the rules --------------------------------------


async def test_scan_produces_advisory_risk_scores_with_stored_explanations(
    session_a, tenant_a, scanned
):
    """The scan runs the statistical model alongside the rules and persists the flagged
    lines — each with the model version and its exact Shapley attribution stored at
    scoring time, so 'why' survives even after the model moves."""
    entity_id, _ = scanned
    scores = await RiskService(session_a, tenant_a, REVIEWER).list_risk_scores(
        entity_id=entity_id, period_key="2026-Q2"
    )
    assert scores  # at least one line surfaced
    top = scores[0]
    assert top.rank == 1
    assert top.model_version.startswith("isoforest")
    assert top.attributions  # the Shapley explanation, stored
    assert all("feature" in a and "contribution" in a for a in top.attributions)


async def test_rescanning_replaces_risk_scores_deterministically(session_a, tenant_a, scanned):
    """Scores are a deterministic function of the population, so a re-scan replaces them
    rather than accumulating — same count, identical values."""
    entity_id, _ = scanned
    service = RiskService(session_a, tenant_a, REVIEWER)
    before = await service.list_risk_scores(entity_id=entity_id, period_key="2026-Q2")
    await service.scan(entity_id=entity_id, period_key="2026-Q2")
    after = await service.list_risk_scores(entity_id=entity_id, period_key="2026-Q2")
    assert len(before) == len(after)
    assert [float(s.score) for s in before] == [float(s.score) for s in after]


async def test_scan_records_zero_result_distinctly(session_a, tenant_a):
    """A clean population yields a scan with zero flags — not the absence of a scan."""
    from taxos_core.risk.models import AnomalyScan

    entity = await EntityService(session_a, tenant_a, REVIEWER).create_entity(
        code="UK-09", name="Clean Ltd", jurisdiction_code="UK"
    )
    clean = (
        b"document_ref,document_date,counterparty,net_amount,vat_amount,vat_code,currency\n"
        b"PI-1,2026-04-10,Alpha Ltd,1234.56,246.91,S20,GBP\n"
        b"PI-2,2026-04-11,Beta Ltd,987.65,197.53,S20,GBP\n"
    )
    await IngestionService(session_a, tenant_a, REVIEWER).ingest_csv(
        entity_id=entity.id,
        period_key="2026-Q2",
        source_type="AP",
        filename="clean.csv",
        content=clean,
    )
    result = await RiskService(session_a, tenant_a, REVIEWER).scan(
        entity_id=entity.id, period_key="2026-Q2"
    )
    assert result.flagged == 0
    scans = (await session_a.execute(select(AnomalyScan))).scalars().all()
    assert len(scans) == 1 and scans[0].rows_scanned == 2  # the scan happened
