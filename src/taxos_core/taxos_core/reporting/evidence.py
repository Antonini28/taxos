"""Evidence pack assembly (US-603).

The payoff of evidence-by-default: an enquiry response that used to take weeks becomes a
download. A pack is assembled only for an APPROVED work item (Phase 2 doc 10 §5) — you
cannot export evidence for something no human has signed off — and it verifies the audit
chain as it builds, so the pack asserts its own integrity rather than merely presenting data.

Rendered as a single self-contained HTML document: no external assets, prints to PDF
natively, opens anywhere, and stays readable years from now without a viewer.
"""

import html
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taxos_core.agents.models import AgentRun, AgentStep
from taxos_core.audit.verify import verify_chain
from taxos_core.compliance.service import ComputationService
from taxos_core.masterdata.models import LegalEntity
from taxos_core.risk.models import Anomaly
from taxos_core.workflow.models import Approval, WorkflowTransition, WorkItem
from taxos_core.workflow.states import WorkItemState


class NotApprovedError(Exception):
    """A pack cannot be built for an item no human has approved (GP-1). Exporting evidence
    for unapproved work would be asserting a position nobody has taken."""


@dataclass
class EvidencePack:
    work_item_id: uuid.UUID
    title: str
    entity_name: str
    period_key: str
    generated_at: datetime
    generated_by: str
    chain_verified: bool
    chain_events: int
    computation: dict = field(default_factory=dict)
    boxes: list[dict] = field(default_factory=list)
    lineage: dict = field(default_factory=dict)  # box_id -> [entries]
    approvals: list[dict] = field(default_factory=list)
    transitions: list[dict] = field(default_factory=list)
    agent_steps: list[dict] = field(default_factory=list)
    anomalies: list[dict] = field(default_factory=list)


class EvidenceService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID, actor) -> None:  # noqa: ANN001
        self._s = session
        self._tenant_id = tenant_id
        self._actor = actor

    async def build(self, work_item_id: uuid.UUID) -> EvidencePack:
        item = (
            await self._s.execute(select(WorkItem).where(WorkItem.id == work_item_id))
        ).scalar_one_or_none()
        if item is None:
            raise NotApprovedError(f"Work item {work_item_id} not found")
        if item.state != WorkItemState.APPROVED:
            raise NotApprovedError(
                f"Work item is {item.state}; an evidence pack is only produced for an "
                "APPROVED item — the pack attests to a signed-off position."
            )

        entity = (
            await self._s.execute(select(LegalEntity).where(LegalEntity.id == item.entity_id))
        ).scalar_one()

        chain = await verify_chain(self._s, self._tenant_id)

        pack = EvidencePack(
            work_item_id=item.id,
            title=item.title,
            entity_name=entity.name,
            period_key=item.period_key,
            generated_at=datetime.now(UTC),
            generated_by=self._actor.ref,
            chain_verified=chain.verified,
            chain_events=chain.events_checked,
        )

        # Computation + lineage per box (US-202): the figures and their provenance.
        if item.computation_id:
            comp_service = ComputationService(self._s, self._tenant_id, self._actor)
            computation = await comp_service.get_computation(item.computation_id)
            if computation is not None:
                pack.computation = {
                    "pack_ref": computation.pack_ref,
                    "engine_version": computation.engine_version,
                    "inputs_hash": computation.inputs_hash,
                    "result_hash": computation.result_hash,
                }
                lines = await comp_service.get_lines(item.computation_id)
                pack.boxes = [
                    {"box_id": ln.box_id, "label": ln.label, "value": str(ln.value)} for ln in lines
                ]
                for line in lines:
                    entries = await comp_service.get_lineage(item.computation_id, line.box_id)
                    if entries:
                        pack.lineage[line.box_id] = [
                            {
                                "document_ref": e.document_ref,
                                "counterparty": e.counterparty,
                                "kind": e.kind,
                                "amount": str(e.amount),
                                "vat_code": e.vat_code,
                                "citation_ref": e.citation_ref,
                            }
                            for e in entries
                        ]

        # Approvals — who signed, bound to which content hash.
        approvals = (
            (
                await self._s.execute(
                    select(Approval)
                    .where(Approval.work_item_id == item.id)
                    .order_by(Approval.granted_at)
                )
            )
            .scalars()
            .all()
        )
        pack.approvals = [
            {
                "approver": a.approver,
                "content_hash": a.content_hash,
                "comment": a.comment,
                "granted_at": a.granted_at.isoformat(),
                "voided": a.voided,
            }
            for a in approvals
        ]

        # The item's own history.
        transitions = (
            (
                await self._s.execute(
                    select(WorkflowTransition)
                    .where(WorkflowTransition.work_item_id == item.id)
                    .order_by(WorkflowTransition.occurred_at)
                )
            )
            .scalars()
            .all()
        )
        pack.transitions = [
            {
                "from": t.from_state,
                "to": t.to_state,
                "actor": t.actor,
                "at": t.occurred_at.isoformat(),
            }
            for t in transitions
        ]

        # The agent run that prepared it, if any (FR-302 trace).
        runs = (
            (await self._s.execute(select(AgentRun).where(AgentRun.work_item_id == item.id)))
            .scalars()
            .all()
        )
        for run in runs:
            steps = (
                (
                    await self._s.execute(
                        select(AgentStep)
                        .where(AgentStep.run_id == run.id)
                        .order_by(AgentStep.sequence)
                    )
                )
                .scalars()
                .all()
            )
            pack.agent_steps.extend(
                {
                    "agent": s.agent,
                    "goal": s.goal,
                    "status": s.status,
                    "tools": [c.get("tool") for c in s.tool_calls],
                    "confidence_basis": s.confidence_basis,
                }
                for s in steps
            )

        # Anomalies scanned for the period.
        anomalies = (
            (
                await self._s.execute(
                    select(Anomaly).where(
                        Anomaly.entity_id == item.entity_id, Anomaly.period_key == item.period_key
                    )
                )
            )
            .scalars()
            .all()
        )
        pack.anomalies = [
            {
                "document_ref": a.document_ref,
                "type": a.anomaly_type,
                "severity": a.severity,
                "status": a.status,
                "explanation": a.explanation,
                "disposition": a.disposition_reason,
            }
            for a in anomalies
        ]

        return pack


def _money(value: str) -> str:
    return f"£{Decimal(value):,.2f}"


def _box_ref(box_id: str) -> str:
    """A short, tax-type-neutral reference for a box. VAT numbers its boxes ("Box 1"); a
    Corporation Tax pack names its lines ("PBT", "TTP"), so a numeric suffix becomes "Box N"
    and anything else becomes its uppercased name."""
    suffix = box_id.replace("box_", "")
    return f"Box {suffix}" if suffix.isdigit() else suffix.upper()


def render_html(pack: EvidencePack) -> str:
    """A single self-contained HTML document. Deliberately plain and print-friendly —
    an evidence pack is a legal artifact, not a marketing page."""
    e = html.escape

    def box_rows() -> str:
        rows = []
        for box in pack.boxes:
            lineage = pack.lineage.get(box["box_id"], [])
            rows.append(
                f"<tr><td class='mono'>{e(_box_ref(box['box_id']))}</td>"
                f"<td>{e(box['label'])}</td>"
                f"<td class='num'>{_money(box['value'])}</td>"
                f"<td class='num'>{len(lineage)}</td></tr>"
            )
        return "".join(rows)

    def lineage_sections() -> str:
        out = []
        for box_id, entries in pack.lineage.items():
            rows = "".join(
                f"<tr><td class='mono'>{e(x['document_ref'])}</td><td>{e(x['counterparty'])}</td>"
                f"<td>{e(x['vat_code'])} {e(x['kind'].replace('_', ' '))}</td>"
                f"<td class='num'>{_money(x['amount'])}</td>"
                f"<td class='mono'>{e(x['citation_ref'])}</td></tr>"
                for x in entries
            )
            total = sum(Decimal(x["amount"]) for x in entries)
            out.append(
                f"<h3>{e(_box_ref(box_id))} — contributing rows</h3>"
                "<table><thead><tr><th>Document</th><th>Counterparty</th><th>Treatment</th>"
                "<th class='num'>Amount</th><th>Authority</th></tr></thead>"
                f"<tbody>{rows}</tbody>"
                f"<tfoot><tr><td colspan='3'>Total</td><td class='num'>{_money(str(total))}</td>"
                "<td></td></tr></tfoot></table>"
            )
        return "".join(out)

    approvals = "".join(
        f"<li><strong>{e(a['approver'].replace('user:', ''))}</strong> "
        f"— {e(a['granted_at'])}<br><span class='mono small'>bound to {e(a['content_hash'])}</span>"
        + (f"<br>“{e(a['comment'])}”" if a["comment"] else "")
        + ("<br><span class='void'>VOIDED</span>" if a["voided"] else "")
        + "</li>"
        for a in pack.approvals
    )
    transitions = "".join(
        f"<li>{e(t['from'])} → <strong>{e(t['to'])}</strong> "
        f"by {e(t['actor'].replace('user:', '').replace('agent:', 'agent '))} — {e(t['at'])}</li>"
        for t in pack.transitions
    )
    agent = "".join(
        f"<li><span class='mono'>{e(s['agent'])}</span> {e(s['goal'])} — {e(s['status'])} "
        f"<span class='small'>(tools: {e(', '.join(t for t in s['tools'] if t))}; "
        f"{e(s['confidence_basis'].lower())})</span></li>"
        for s in pack.agent_steps
    )
    anomalies = "".join(
        f"<li><span class='sev-{e(a['severity'].lower())}'>{e(a['severity'])}</span> "
        f"<span class='mono'>{e(a['document_ref'])}</span> — {e(a['explanation'])} "
        f"<span class='small'>[{e(a['status'])}"
        + (f", {e(a['disposition'])}" if a["disposition"] else "")
        + "]</span></li>"
        for a in pack.anomalies
    )

    chain_badge = (
        f"<span class='ok'>✓ Audit chain verified — {pack.chain_events} events</span>"
        if pack.chain_verified
        else "<span class='fail'>✗ AUDIT CHAIN VERIFICATION FAILED</span>"
    )

    return f"""<!doctype html>
<html lang="en-GB"><head><meta charset="utf-8">
<title>Evidence Pack — {e(pack.title)}</title>
<style>
  body {{ font-family: system-ui, -apple-system, "Segoe UI", sans-serif; color: #111;
         max-width: 820px; margin: 32px auto; padding: 0 24px; line-height: 1.5; }}
  h1 {{ font-size: 22px; margin-bottom: 2px; }}
  h2 {{ font-size: 16px; margin-top: 28px; border-bottom: 1px solid #ddd; padding-bottom: 4px; }}
  h3 {{ font-size: 13px; margin-top: 16px; color: #444; }}
  .meta {{ color: #555; font-size: 13px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 8px; }}
  th, td {{ text-align: left; padding: 4px 8px; border-bottom: 1px solid #eee; }}
  th {{ font-size: 11px; text-transform: uppercase; letter-spacing: .04em; color: #666; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .mono {{ font-family: "Cascadia Code", Consolas, monospace; font-size: 12px; }}
  .small {{ font-size: 11px; color: #666; }}
  tfoot td {{ font-weight: 600; border-top: 2px solid #ccc; }}
  ul {{ font-size: 13px; padding-left: 18px; }}
  li {{ margin-bottom: 6px; }}
  .ok {{ color: #0a7d0a; font-weight: 600; }}
  .fail {{ color: #c0392b; font-weight: 700; }}
  .void {{ color: #c0392b; font-weight: 600; }}
  .sev-high {{ color: #c0392b; font-weight: 600; }}
  .sev-medium {{ color: #b8651b; font-weight: 600; }}
  .sev-low {{ color: #888; }}
  .banner {{ background: #f4f8ff; border: 1px solid #cfe0fb; border-radius: 6px;
            padding: 10px 14px; margin: 16px 0; font-size: 13px; }}
  footer {{ margin-top: 40px; color: #999; font-size: 11px; border-top: 1px solid #eee;
           padding-top: 12px; }}
</style></head><body>
<h1>Evidence Pack</h1>
<div class="meta">{e(pack.title)} · {e(pack.entity_name)} · {e(pack.period_key)}</div>
<div class="banner">{chain_badge}<br>
  <span class="small">Generated {e(pack.generated_at.strftime("%Y-%m-%d %H:%M UTC"))}
  by {e(pack.generated_by.replace("user:", ""))}. Every figure below traces to a source
  transaction; every approval binds to a content hash; the audit chain was re-verified as
  this pack was assembled.</span></div>

<h2>Computation</h2>
<div class="meta mono small">rule pack {e(pack.computation.get("pack_ref", "—"))} ·
  engine {e(pack.computation.get("engine_version", "—"))} ·
  result hash {e(pack.computation.get("result_hash", "—"))}</div>
<table><thead><tr><th>Ref</th><th>Description</th><th class="num">Value</th>
  <th class="num">Sources</th></tr></thead><tbody>{box_rows()}</tbody></table>

<h2>Lineage</h2>
{lineage_sections() or '<p class="small">No lineage recorded.</p>'}

<h2>Approvals</h2>
<ul>{approvals or '<li class="small">None.</li>'}</ul>

<h2>Workflow history</h2>
<ul>{transitions or '<li class="small">None.</li>'}</ul>

<h2>Agent preparation trace</h2>
<ul>{agent or '<li class="small">Not agent-prepared.</li>'}</ul>

<h2>Anomaly review</h2>
<ul>{anomalies or '<li class="small">No anomalies flagged for the period.</li>'}</ul>

<footer>TaxOS evidence pack · work item {e(str(pack.work_item_id))} ·
  This document is self-contained and reproducible from the platform's immutable records.</footer>
</body></html>"""
