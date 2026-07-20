# 03 — Core Agent Catalogue (MVP / R1)

Specification template per agent: Purpose · Responsibilities · Tools (Tool Gateway grants) · Memory · Prompt (system-prompt core; full versioned prompts live in `services/agents/prompts/`) · Inputs/Outputs (envelope types) · Error handling (deltas from the uniform taxonomy, doc 02 §6) · Escalation · Evaluation metrics.
Common to all agents and therefore not repeated: uniform error taxonomy; structured outputs only; citations required for `GROUNDED` claims; all actions traced (FR-302); tenant/entity scope from the run context, never from model output.

---

## 3.1 Supervisor

| Field | Specification |
|---|---|
| **Purpose** | Convert a human instruction or triggering event into a bounded, budgeted, tool-feasible plan; route work to specialists; track progress; guarantee every run ends in HANDOFF, escalation, or clean failure. |
| **Responsibilities** | Parse instruction → goal decomposition; feasibility check against agent registry grants; budget allocation per step; sequencing with data dependencies; monitoring step results; invoking Critic; assembling the HANDOFF package (work item payload); episodic-memory consultation ("what went wrong for this entity last quarter"). |
| **Tools** | `get_obligation`, `get_entity_profile`, `list_validated_batches` (read-only planning context); `create_work_item`, `raise_escalation`, `update_run_plan`. **No domain computation tools** — the Supervisor plans, it never does. |
| **Memory** | Working (own graph state); episodic read (last-N episodes for entity/obligation); procedural (plan templates per obligation type — versioned playbooks, e.g. `vat-quarterly-v3`). |
| **Prompt (core)** | *"You are the Supervisor of a governed tax-agent team. You produce PLANS, never tax content. A plan is a DAG of steps; each step names one registered agent, one goal, typed context refs, and a budget. You may only use agents and tools listed in the provided registry extract. If the instruction is ambiguous, infeasible, or exceeds granted capabilities, output an ESCALATION, not a guess. Plans must terminate at create_work_item — you have no approval or filing capability, and no plan may attempt one."* + registry extract + playbook + episodic notes. |
| **Inputs** | `AgentRunRequested` event (instruction text or scheduled trigger, tenant/entity/period scope, requesting user). |
| **Outputs** | Validated `RunPlan` (persisted, streamed); per-step `TaskEnvelope`s; final `HandoffPackage` (computation refs, narratives, anomaly refs, citations, cost summary). |
| **Error handling** | Plan validation failures (unknown agent, ungranted tool, unbounded loop) are *rejections* pre-execution — the graph refuses to start; mid-run step failure triggers re-plan (≤1 re-plan, then escalate). |
| **Escalation** | To requesting user (ambiguity) or preparer queue (data gaps aggregated from specialists); always names the exact blocker and what would unblock it. |
| **Evaluation** | Plan validity rate (target 100% post-validation — validator catches, metric watches generation quality); plan efficiency (steps vs playbook baseline); % runs reaching HANDOFF without human rescue (≥95% on golden scenarios); escalation precision (escalations that reviewers mark "correctly raised" ≥90%); re-plan rate. |

---

## 3.2 Data agent ("Tax Data Engineer")

| Field | Specification |
|---|---|
| **Purpose** | Confirm, assemble, and quality-narrate the data foundation for a compliance step — the agent that answers "do we have everything, and is it trustworthy?" |
| **Responsibilities** | Input inventory vs obligation data requirements (from pack manifest); validation-report interpretation (turn rule-level quarantine stats into a preparer-readable data-quality narrative); period-over-period volume/control-total sanity checks; gap identification with named sources. |
| **Tools** | `list_validated_batches`, `get_validation_report`, `get_quarantine_summary`, `get_batch_stats`, `get_prior_period_stats`, `get_pack_data_requirements`. All read-only — the Data agent never mutates data (pipelines do; it interprets). |
| **Memory** | Working; episodic read/write (data issues per entity recur — late payroll extracts, chronic VAT-code errors at supplier X). |
| **Prompt (core)** | *"You are a tax data engineer. Given an obligation's data requirements and the available validated batches, produce a DataReadinessReport. You interpret validation evidence; you never invent figures, never estimate missing data, and never mark requirements met without a batch reference. Quarantine patterns should be explained in business terms with the underlying rule cited. If any required source is missing or anomalously small vs history, report status=GAPS with specifics."* |
| **Inputs** | `TaskEnvelope{goal: assess readiness, context: obligation_ref, period}`. |
| **Outputs** | `DataReadinessReport{status: READY\|GAPS, requirement_matrix, quality_narrative, gaps[], confidence}` — the Supervisor's go/no-go for computation steps. |
| **Error handling** | Uniform taxonomy; notably: volume anomaly vs history (>30% deviation) forces `GAPS` with `DETERMINISTIC` basis even when all sources technically present — suspicious completeness is a gap. |
| **Escalation** | Named-source gaps → preparer queue with "what to upload"; systemic quality collapse (quarantine ratio spike) → Tax Tech Lead (P5) queue. |
| **Evaluation** | Gap recall on golden set (seeded missing/short sources — ≥98%: this agent missing a gap poisons everything downstream); false-gap rate (<5%); narrative faithfulness (critic/judge rubric: every claim traceable to a report field); readiness-report acceptance rate by preparers. |

---

## 3.3 VAT agent (first TaxDomainAgent instance)

| Field | Specification |
|---|---|
| **Purpose** | Produce a review-ready draft VAT return package: trigger the deterministic computation, then explain it — variances, exceptions, positions — with citations. The agent is the *analyst around* the engine, never the calculator (AP-2). |
| **Responsibilities** | Invoke engine on validated inputs; period-over-period and box-level variance analysis; exception narrative (quarantine impacts, unusual codes); flag judgement areas (partial exemption, reverse-charge patterns) with rule citations; assemble draft-return package for review. |
| **Tools** | `run_vat_computation` (idempotent engine invocation → snapshot ref), `get_computation`, `get_computation_lineage`, `get_prior_computations`, `get_pack_rule` (rule text + HMRC citation by rule id), `search_knowledge` (R2). No write tools beyond computation trigger. |
| **Memory** | Working; episodic (entity's recurring variance explanations — "Box 6 spike each Q4 = seasonal promotions"); semantic (R2: HMRC VAT manuals). |
| **Prompt (core)** | *"You are a UK VAT analyst. Box values come exclusively from the computation snapshot — you never compute, adjust, or round figures; if a figure looks wrong, say so in the narrative, do not 'correct' it. Every technical assertion must cite either a pack rule (with HMRC reference) or a retrieved source. Variances ≥ the materiality threshold require an explanation grounded in lineage data or an explicit 'unexplained — flagged for review'. Unexplained is acceptable; invented explanations are not."* |
| **Inputs** | `TaskEnvelope{goal: draft return, context: obligation_ref, DataReadinessReport ref}`. |
| **Outputs** | `DraftReturnPackage{computation_ref, variance_analysis[], exceptions[], judgement_flags[], narrative, citations[], confidence}`. Box values are refs into the snapshot — the package physically cannot contain agent-authored figures (schema has no numeric box fields). |
| **Error handling** | Engine failure (pack/schema error) → escalate to P5 immediately (rule infrastructure problem, not agent-solvable); materially-large unexplained variance → package still completes with prominent flag (blocking on explanation would incentivise confabulation). |
| **Escalation** | Judgement calls (e.g. partial-exemption method question) → reviewer queue with both interpretations cited; engine/pack errors → P5. |
| **Evaluation** | Figure-integrity invariant (0 tolerance: no numeric in narrative absent from snapshot/lineage — checked mechanically per output); variance-explanation faithfulness (judge rubric vs lineage evidence, ≥95%); citation validity (cited rule exists + supports claim, ≥95%); reviewer edit-distance on narratives (trend metric); judgement-flag recall on golden scenarios with seeded issues (≥90%). |

---

## 3.4 Fraud agent

| Field | Specification |
|---|---|
| **Purpose** | Front the deterministic anomaly pipeline: contextualise scored anomalies into investigable cases, prioritise, and narrate — the ML detects, the agent investigates. |
| **Responsibilities** | Trigger/collect scan results; cluster related anomalies into cases (same vendor/pattern/period); enrich with transaction context via lineage; produce ranked case summaries with recommended next actions; route by severity per policy. |
| **Tools** | `trigger_anomaly_scan` (idempotent per batch-set), `list_anomalies`, `get_anomaly_explanation` (rule trace or SHAP payload), `get_transaction_context`, `get_vendor_history`, `create_anomaly_case` (groups anomalies — the only write; dispositions remain human-only, FR-506). |
| **Memory** | Working; episodic (dispositions history per pattern/vendor — "this 'duplicate' is a legitimate recurring instalment, dismissed 3× with reason"). Reading disposition history prevents re-flagging noise at the *case* level while the underlying detector stays untouched (detector tuning is an ML-lifecycle decision, not an agent behaviour). |
| **Prompt (core)** | *"You are a forensic tax analyst. Anomaly scores and explanations come from the detection pipeline — you never re-score, suppress, or downgrade an anomaly; your judgement operates on grouping, prioritisation, and narrative. Every case summary must reference the underlying anomaly ids and their explanation payloads. Recommended actions are investigative steps for a human, never dispositions. Prior dismissals with reasons may inform priority, and you must cite the prior disposition when used."* |
| **Inputs** | `TaskEnvelope{goal: anomaly review, context: batch_refs \| period}` (in-cycle) or scheduled sweep trigger. |
| **Outputs** | `AnomalyCaseReport{cases[]: {anomaly_refs, pattern, materiality, context_narrative, recommended_actions, prior_disposition_refs}, severity_summary, confidence}`. |
| **Error handling** | Scan pipeline failure → escalate P5 (never report "no anomalies" on a failed scan — absence of evidence is reported as absence of *scan*); SHAP payload missing (R2) → case proceeds flagged "explanation unavailable". |
| **Escalation** | Severity ≥ HIGH or materiality ≥ threshold → immediate Risk Lead (P3) notification, not just queue placement; suspected systemic fraud pattern (multi-entity) → P3 + P1 per policy config. |
| **Evaluation** | Case grouping quality (judge rubric + P3 feedback: % cases accepted as well-formed ≥85%); triage agreement (agent priority vs P3 final priority, Kendall-τ trend); zero-suppression invariant (every pipeline anomaly appears in exactly one case or explicit singleton — mechanical check); narrative faithfulness to explanation payloads (≥95%); time-to-first-disposition (business metric the agent exists to improve). |

---

## 3.5 Reporting agent

| Field | Specification |
|---|---|
| **Purpose** | Assemble human-audience artifacts — run summaries, review packages, (R3) board packs — from approved/traceable platform data. The last mile between structured truth and executive communication. |
| **Responsibilities** | HANDOFF package narrative (what was done, what needs attention, where the evidence is); review-package formatting for the approval UI; KPI commentary drafting against `rpt_*` aggregates; (R3) scheduled report assembly into templates. |
| **Tools** | `get_computation`, `get_anomaly_cases`, `get_workflow_history`, `get_dashboard_aggregates`, `render_report` (template + data refs → document artifact in Blob). Distribution is **not** a tool — generated reports enter the approval workflow (FR-603). |
| **Memory** | Working; procedural (report templates, house style, per-audience register — P4 gets three sentences, P3 gets the detail). |
| **Prompt (core)** | *"You are an executive reporting specialist for a tax platform. Every figure you present must be a reference to platform data — computations, aggregates, cases — rendered via the template engine; you write connective narrative, headlines, and interpretation, never numbers from memory. Match register to audience profile. Flag data-freshness (as_of timestamps) wherever aggregates are used. You cannot send, publish, or distribute anything."* |
| **Inputs** | `TaskEnvelope{goal: assemble package, context: run outputs \| report template + period}`. |
| **Outputs** | `ReportArtifact{template_id, data_refs[], narrative_blocks[], artifact_blob_ref, confidence}`. |
| **Error handling** | Missing data ref at render time → hard fail + escalate (a report with silent blanks is worse than no report); stale aggregate (as_of older than policy) → render with prominent staleness banner + note in output. |
| **Escalation** | Template/data-contract mismatches → P5; content-judgement questions (e.g. "should this exposure appear in the board pack") → requesting user — the agent surfaces, humans decide inclusion. |
| **Evaluation** | Figure-provenance invariant (0 unreferenced numerics — mechanical); narrative faithfulness (judge rubric ≥95%); audience-register score (judge rubric per persona profile); human edit-distance before approval (trend); report approval-without-change rate. |

---

## 3.6 Critic agent

| Field | Specification |
|---|---|
| **Purpose** | Rubric-driven quality gate between specialist output and human review (FR-305) — catches confabulation, citation failure, and figure-integrity violations before they cost a reviewer's time or trust. |
| **Responsibilities** | Evaluate `ResultEnvelope`s against the per-agent rubric (versioned in repo); verify citations resolve and support their claims (mechanical resolution + semantic support check); verify figure provenance mechanically; produce pass/revise verdicts with specific, actionable findings. |
| **Tools** | `resolve_citation` (does ref exist + return passage), `get_computation` / `get_computation_lineage` (figure verification), `get_rubric` (versioned rubric fetch). Read-only by construction. |
| **Memory** | Working only — the Critic is deliberately stateless across runs (no drift toward leniency via accumulated context; consistency is its product). Procedural rubrics are its only persistent knowledge. |
| **Prompt (core)** | *"You are a quality reviewer. Judge ONLY against the provided rubric and the evidence returned by your verification tools. You do not rewrite the work, suggest improvements beyond the rubric, or soften findings. Each finding: rubric criterion, severity, exact location, evidence. Verdict PASS requires zero critical findings. You are evaluating the work, not the agent; identical work must receive identical verdicts."* |
| **Inputs** | Specialist `ResultEnvelope` + rubric id + verification context. |
| **Outputs** | `CritiqueReport{verdict: PASS\|REVISE, findings[]: {criterion, severity, location, evidence}, checked: {citations_resolved, figures_verified}}`. |
| **Error handling** | Verification tool failure → verdict `REVISE` with infrastructure finding (fail closed — unverifiable work does not pass); rubric missing/version-mismatch → run-level escalation to P5. |
| **Escalation** | Two consecutive REVISE on same step → to human with both drafts + findings (doc 02 §6); pattern telemetry (rejection-rate spike per agent) → alerts P5 (possible prompt/model regression). |
| **Evaluation** | Agreement with human reviewers on golden set (κ ≥ 0.8 on pass/revise); seeded-defect catch rate (documents with planted confabulations/citation errors — ≥95% critical-defect recall); false-rejection rate (<10%); verdict consistency (identical input replay ⇒ identical verdict — temperature 0, checked in CI). |
