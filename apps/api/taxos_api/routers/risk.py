"""Fraud & risk endpoints (US-801).

The detectors advise; the disposition is a human act with a reason code. There is no
endpoint that auto-confirms or auto-dismisses — ML-1 in the API surface.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from taxos_core.risk.models import CONFIRM_REASONS, DISMISS_REASONS
from taxos_core.risk.service import InvalidDispositionError, RiskService

from taxos_api.deps import Principal, current_principal, db_session
from taxos_api.errors import NotFoundError, ValidationFailed

router = APIRouter(prefix="/anomalies", tags=["risk"])

PrincipalDep = Annotated[Principal, Depends(current_principal)]
SessionDep = Annotated[AsyncSession, Depends(db_session)]


class ScanRequest(BaseModel):
    entity_id: uuid.UUID
    period_key: str


class DispositionRequest(BaseModel):
    confirm: bool
    reason: str
    note: str | None = None


class AnomalyOut(BaseModel):
    id: uuid.UUID
    document_ref: str
    detector: str
    anomaly_type: str
    severity: str
    explanation: str
    evidence: dict
    status: str
    disposition_reason: str | None
    dispositioned_by: str | None
    created_at: str


class SummaryOut(BaseModel):
    open: int
    confirmed: int
    dismissed: int
    high_open: int


class AttributionOut(BaseModel):
    feature: str
    value: float
    contribution: float


class RiskScoreOut(BaseModel):
    document_ref: str
    counterparty: str
    score: float
    rank: int
    percentile: float
    reason: str
    model_version: str
    attributions: list[AttributionOut]


class FeatureImportanceOut(BaseModel):
    feature: str
    contribution: float


class ModelStatusOut(BaseModel):
    """Rung 3 readiness. When not sufficient, the counts are the evidence for the refusal."""

    sufficient: bool
    model_version: str
    note: str
    n_confirmed: int
    n_true_negative: int
    n_censored_excluded: int
    min_per_class: int
    model_auc: float | None
    baseline_auc: float | None
    beats_baseline: bool | None
    feature_importance: list[FeatureImportanceOut]


def _service(session: AsyncSession, principal: Principal) -> RiskService:
    return RiskService(session, principal.tenant_id, principal.actor)


def _out(a) -> AnomalyOut:  # noqa: ANN001
    return AnomalyOut(
        id=a.id,
        document_ref=a.document_ref,
        detector=a.detector,
        anomaly_type=a.anomaly_type,
        severity=a.severity,
        explanation=a.explanation,
        evidence=a.evidence,
        status=a.status,
        disposition_reason=a.disposition_reason,
        dispositioned_by=a.dispositioned_by,
        created_at=a.created_at.isoformat(),
    )


@router.get("/reasons")
async def disposition_reasons() -> dict[str, dict[str, str]]:
    """The reason taxonomy — the label space. Exposed so the UI offers exactly these,
    rather than a free-text box that would produce unlabelled examples."""
    return {"confirm": CONFIRM_REASONS, "dismiss": DISMISS_REASONS}


@router.get("/summary", response_model=SummaryOut)
async def summary(principal: PrincipalDep, session: SessionDep) -> SummaryOut:
    return SummaryOut(**await _service(session, principal).summary())


@router.get("", response_model=list[AnomalyOut])
async def list_anomalies(
    principal: PrincipalDep, session: SessionDep, status: str | None = None
) -> list[AnomalyOut]:
    anomalies = await _service(session, principal).list_anomalies(status=status)
    return [_out(a) for a in anomalies]


@router.get("/risk-scores", response_model=list[RiskScoreOut])
async def risk_scores(
    entity_id: uuid.UUID, period_key: str, principal: PrincipalDep, session: SessionDep
) -> list[RiskScoreOut]:
    """The Rung-2 model's flagged lines for an entity-period, with their Shapley reasons.
    Advisory context beside the rule anomalies — there is no endpoint that acts on a score."""
    scores = await _service(session, principal).list_risk_scores(
        entity_id=entity_id, period_key=period_key
    )
    return [
        RiskScoreOut(
            document_ref=s.document_ref,
            counterparty=s.counterparty,
            score=float(s.score),
            rank=s.rank,
            percentile=float(s.percentile),
            reason=s.reason,
            model_version=s.model_version,
            attributions=[AttributionOut(**a) for a in s.attributions],
        )
        for s in scores
    ]


@router.get("/model-status", response_model=ModelStatusOut)
async def model_status(principal: PrincipalDep, session: SessionDep) -> ModelStatusOut:
    """Rung-3 readiness: does the supervised model have enough labelled dispositions to train?
    When it does not, this returns an evidenced 'not yet' with the counts — the same posture
    the knowledge layer takes for INSUFFICIENT_SOURCES."""
    report = await _service(session, principal).supervised_status()
    return ModelStatusOut(
        sufficient=report.sufficient,
        model_version=report.model_version,
        note=report.note,
        n_confirmed=report.n_confirmed,
        n_true_negative=report.n_true_negative,
        n_censored_excluded=report.n_censored_excluded,
        min_per_class=report.min_per_class,
        model_auc=report.model_auc,
        baseline_auc=report.baseline_auc,
        beats_baseline=report.beats_baseline,
        feature_importance=[
            FeatureImportanceOut(feature=a.feature, contribution=a.contribution)
            for a in report.feature_importance
        ],
    )


@router.post("/scan", status_code=status.HTTP_201_CREATED)
async def scan(body: ScanRequest, principal: PrincipalDep, session: SessionDep) -> dict:
    result = await _service(session, principal).scan(
        entity_id=body.entity_id, period_key=body.period_key
    )
    return {
        "scan_id": str(result.scan_id),
        "rows_scanned": result.rows_scanned,
        "flagged": result.flagged,
        "new_anomalies": result.new_anomalies,
    }


@router.post("/{anomaly_id}/disposition", response_model=AnomalyOut)
async def disposition(
    anomaly_id: uuid.UUID,
    body: DispositionRequest,
    principal: PrincipalDep,
    session: SessionDep,
) -> AnomalyOut:
    service = _service(session, principal)
    # Existence is checked here so a genuine error inside disposition is never swallowed
    # by a broad except and mislabelled "not found".
    if not any(a.id == anomaly_id for a in await service.list_anomalies()):
        raise NotFoundError(f"Anomaly {anomaly_id} not found")
    try:
        anomaly = await service.disposition(
            anomaly_id, confirm=body.confirm, reason=body.reason, note=body.note
        )
    except InvalidDispositionError as exc:
        raise ValidationFailed(str(exc)) from exc
    return _out(anomaly)
