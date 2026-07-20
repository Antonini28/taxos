# 04 — Extended Agent Catalogue (R2–R4)

Same specification fields as doc 03, in compact form. Each agent still carries the full contract: purpose, responsibilities, tools, memory, prompt core, I/O, error handling, escalation, evaluation.

---

## 4.1 The TaxDomainAgent template (AP-3 applied to agents)

VAT (doc 03), Corporate Tax, Withholding Tax, Payroll Tax, and Indirect Tax agents are **instances of one template**, parameterised by registry config:

```yaml
# registry/agents/wht.yaml (illustrative)
agent: wht
template: tax_domain_agent
release: R4
model_route: standard
content_pack_family: uk-wht
tools:  [run_wht_computation, get_computation, get_computation_lineage,
         get_prior_computations, get_pack_rule, get_treaty_rate, search_knowledge]
prompt_overlay: prompts/domains/wht-v1.md      # domain-specific guidance layered on the template prompt
rubric: rubrics/tax_domain_v2.yaml
confidence_threshold: 0.85
escalation_routes: {judgement: reviewer_queue, engine: p5_queue}
```

Shared by construction: the figure-integrity invariant (no agent-authored numerics — schema-enforced), citation obligations, variance-analysis pattern, error handling, evaluation metric family. Domain-specific: tools (each domain's engine + reference-data lookups), prompt overlay (domain pitfalls and vocabulary), rubric weighting, thresholds. **Adding a tax domain = pack + engine capability (ADR-005) + registry file + prompt overlay + golden set — no new agent code.** This is the same content-pack philosophy that makes jurisdictions addable, applied to the agent tier.

Per-instance notes:

| Instance | Release | Domain-specific tools & notes | Domain eval additions |
|---|---|---|---|
| **Corporate Tax agent** | R2 | `run_ct_computation`, `get_financial_statements` (from Financial Statement agent output), `get_adjustment_schedule`; reasoning-route model (adjustment logic is genuinely harder); prompt overlay covers disallowables, capital allowances interplay, loss/group-relief flags → always judgement-flagged, never resolved by the agent | Adjustment-classification accuracy vs golden CT scenarios (≥95%); group-relief flag recall (100% — these are always human decisions) |
| **Withholding Tax agent** | R4 | `get_treaty_rate` (versioned treaty table lookup — a pack, not an LLM recall); payment-classification suggestions carry `MODEL_JUDGEMENT` basis and route to review below threshold | Payment-classification accuracy (≥92%); treaty-rate citation validity (100% — rate must match table version) |
| **Transfer Pricing agent** | R4 | `get_intercompany_register`, `get_policy_rates`, `compute_variance` (deterministic); monitors actual vs policy, drafts variance memos; **never** proposes arm's-length prices (advisory red line, W-register) | Variance-detection recall on seeded register (100% — arithmetic is deterministic); memo faithfulness (≥95%) |
| **Payroll / Indirect instances** | backlog | Registry stubs exist; activated when packs exist — demonstrating the marginal cost of a new domain is configuration | Template metric family |

---

## 4.2 Research agent (R2)

- **Purpose:** answer tax-technical questions with cited, grounded analysis — the platform's interface to the knowledge corpus (FR-401..403).
- **Responsibilities:** query decomposition; hybrid retrieval orchestration (vector + BM25 + metadata filters); multi-source synthesis with per-claim citations; conflict surfacing (guidance vs legislation vs internal policy); explicit insufficiency verdicts.
- **Tools:** `search_knowledge` (hybrid, filtered), `get_document_passage`, `get_pack_rule`, `list_knowledge_sources` (corpus coverage check — know what you *can't* know).
- **Memory:** working; semantic (the corpus is its domain); episodic off (research must not drift on remembered answers — every question re-grounded).
- **Prompt core:** *"You are a UK tax researcher. Every claim must carry a citation to a retrieved passage; uncited sentences are forbidden. Where sources conflict, present both with authority ranking (legislation > case law > HMRC guidance > internal policy) — you never resolve conflicts. If retrieval does not support an answer, your output is INSUFFICIENT_SOURCES with what was searched. You answer as research, never as advice; recommendations belong to humans."*
- **I/O:** `ResearchQuery{question, jurisdiction, tax, as_of_date}` → `ResearchMemo{answer_blocks[{claim, citations[]}], conflicts[], coverage_note, confidence: GROUNDED}`.
- **Error handling:** retrieval degradation (low scores across the board) ⇒ INSUFFICIENT_SOURCES, never a thin answer; as_of_date outside corpus coverage ⇒ explicit temporal-coverage warning.
- **Escalation:** conflicts and insufficiency → reviewer queue; corpus-gap patterns (repeated insufficiency on a topic) → P5 as knowledge-pipeline backlog signal.
- **Evaluation:** citation-support rate on golden Q&A set (≥95%, NFR-07 — the CI-gated headline metric); insufficiency recall (questions the corpus genuinely can't answer must yield INSUFFICIENT_SOURCES ≥95%); retrieval hit-rate@k on labelled relevance set; authority-ranking correctness on seeded conflicts.

## 4.3 Document agent (R2)

- **Purpose:** turn unstructured documents (invoices, certificates, assessments, correspondence) into validated structured records with provenance.
- **Responsibilities:** classify document type; route to extraction schema; field extraction with per-field confidence + source-region anchors; validation against master data (vendor exists, VAT number checksum, currency plausibility); low-confidence field flagging for human verification queue.
- **Tools:** `get_document` (+ OCR sidecar), `get_extraction_schema`, `submit_extraction` (writes to *staging* — promotion to business data happens through the validation pipeline like any batch), `lookup_vendor`, `validate_vat_number`.
- **Memory:** working; episodic per vendor (layout quirks: "vendor X puts VAT reg in the footer").
- **Prompt core:** *"You extract structured data from tax documents. Every extracted field carries the document region it came from and a confidence. You never infer values not present in the document — absent is absent. Checksum/format validation failures are flagged, not corrected. Ambiguous fields (two candidate totals) are flagged with both candidates."*
- **I/O:** `TaskEnvelope{context: document_ref}` → `ExtractionResult{doc_type, fields[{name, value, region, confidence}], validation_flags[], verification_needed[]}`.
- **Error handling:** unreadable/corrupt OCR ⇒ FAILED with document returned to intake queue; unknown document type ⇒ classify as OTHER + human routing (never force-fit a schema).
- **Escalation:** per-field verification queue (preparer); systematic extraction failure per vendor/format → P5 (schema/OCR backlog).
- **Evaluation:** field-level F1 vs labelled document set (≥97% on invoices — this is a mature ML task; hold it to a high bar); confidence calibration (low-confidence flags must capture ≥95% of actual errors); absent-field discipline (0 hallucinated fields on golden set — hard invariant); human-verification overturn rate (trend).

## 4.4 Risk agent (R2)

- **Purpose:** maintain a living, quantified tax-risk picture per entity/group — aggregating anomaly cases, compliance posture, judgement flags, and ML risk scores into a coherent register (the P3/P1 view).
- **Responsibilities:** synthesise risk inputs into register entries (exposure estimate refs, likelihood band, trend); detect posture deterioration (deadline slippage + quarantine growth + anomaly accumulation = a pattern, not three metrics); draft risk-register updates for P3 confirmation; SHAP narrative translation ("the model scores this high because…" in business language).
- **Tools:** `get_risk_inputs` (aggregated read), `get_anomaly_cases`, `get_compliance_posture`, `get_model_scores_with_explanations`, `draft_register_entry` (staging — P3 confirms entries into the register).
- **Memory:** working; episodic (register history — trend narratives need continuity).
- **Prompt core:** *"You are a tax risk analyst. Exposure figures are references to computed values or documented estimates — you never invent quantifications. Likelihood language follows the house scale (remote/possible/probable) with stated basis. SHAP translations must preserve direction and rank of the actual contributions; simplification may not become distortion. Register entries are drafts for the Risk Lead — you propose, you never confirm."*
- **I/O:** scheduled or event trigger → `RiskAssessmentDraft{register_entries[], posture_narrative, deteriorations[], data_refs[]}`.
- **Error/escalation:** stale inputs (aggregate as_of breaches policy) ⇒ assessment blocked, P5 notified; sharp deterioration ⇒ immediate P3 alert channel, not just queue.
- **Evaluation:** SHAP-translation fidelity (mechanical: direction/rank preservation vs raw payload, 100%); register-draft acceptance rate by P3 (≥80%); deterioration detection lead time vs ground truth on replayed history; exposure-provenance invariant (0 unreferenced figures).

## 4.5 Regulatory Monitor agent (R3)

- **Purpose:** watch configured regulatory sources, classify relevance against each tenant's profile, and produce impact assessments into a human review queue (FR-404) — the platform's answer to regulatory velocity (pain P-03).
- **Responsibilities:** change detection over monitored sources (pipeline-fetched — the agent does not browse); relevance classification vs tenant tax profile (registrations, sectors, schemes); impact-assessment drafting (what changed, who's affected, which pack rules/processes are implicated, suggested effective dates); pack-drift flagging (rule pack cites guidance that changed → content team ticket).
- **Tools:** `list_source_changes` (from the governed fetch pipeline), `get_tenant_tax_profile`, `get_pack_citations` (reverse index: which rules cite this source), `create_impact_assessment` (queue write), `create_content_ticket`.
- **Memory:** working; episodic (assessment history per source — change velocity informs priority); semantic (corpus for context on the changed area).
- **Prompt core:** *"You monitor UK tax regulatory changes. You work only from pipeline-provided change records — never from your training memory of tax law, which is presumed stale. Relevance verdicts cite the specific profile attributes that make a change applicable. Impact assessments distinguish FACT (what the source says changed — quoted) from ASSESSMENT (implication for the tenant — reasoned). Every assessment ends in the review queue; nothing you produce changes platform behaviour directly."*
- **I/O:** `SourceChangeBatch` → `ImpactAssessment{change_ref, relevance:{verdict, profile_basis}, affected_entities[], implicated_rules[], fact_summary, assessment, urgency}` per relevant change.
- **Error/escalation:** ambiguous applicability ⇒ relevance=REVIEW (fail toward human attention); implicated-rule hits always create content tickets regardless of relevance verdict (pack integrity over inbox hygiene).
- **Evaluation:** relevance precision/recall vs P3-labelled change history (recall ≥95% — missing a relevant change is the expensive error; precision ≥70% acceptable); fact/assessment separation (judge rubric, ≥95%); pack-drift catch rate on seeded citation changes (100%); reviewer time-to-triage (business metric).

## 4.6 Audit Readiness agent (R3)

- **Purpose:** continuously verify that the evidence state matches the "assume audit" bar (GP-6) — the agent that finds the missing approval *before* HMRC does.
- **Responsibilities:** evidence completeness sweeps per closed obligation (computation snapshot? approvals? lineage integrity? agent traces? pack signatures?); enquiry-response pack pre-assembly (given an enquiry scope, assemble candidate evidence + gap list); readiness scoring per entity/period; audit-chain verification result interpretation.
- **Tools:** `get_evidence_inventory`, `verify_audit_chain_slice`, `get_workflow_history`, `assemble_evidence_candidate` (staging pack for P3 review), `get_readiness_checklist` (versioned per obligation type).
- **Memory:** working; procedural (readiness checklists are versioned config, mirroring SAO/CCO evidence expectations).
- **Prompt core:** *"You are an audit readiness inspector. You verify evidence against the checklist; verification tool results are your only ground truth. A checklist item is MET only with a resolvable artifact reference. Gaps are reported with remediation owner suggestions. You assemble candidate packs; certification of readiness belongs to the Risk Lead."*
- **I/O:** scheduled sweep or enquiry trigger → `ReadinessReport{scope, checklist_results[{item, status, artifact_ref\|gap}], readiness_score, remediations[]}`.
- **Error/escalation:** chain-verification failure = **critical incident escalation** (P3+P5 immediately — tamper-evidence tripped, doc 07 §6); systemic gaps (same missing artifact class across entities) → process-level ticket to P5.
- **Evaluation:** gap recall on seeded incomplete evidence sets (100% on checklist-covered classes — this agent's whole value is not missing things); artifact-reference validity (100%); readiness-score stability (identical state ⇒ identical score); enquiry-pack assembly time vs manual baseline (business metric).

## 4.7 Financial Statement agent (R2/R3)

- **Purpose:** structured understanding of financial-statement inputs feeding CT computation and analytics — mapping TB/statement lines to the tax-relevant taxonomy with provenance.
- **Responsibilities:** trial-balance/statement mapping to CT computation input taxonomy (pack-defined); YoY movement analysis with tax-relevance flags (new intangibles → capital allowances question); mapping-confidence reporting; unmapped-line escalation.
- **Tools:** `get_trial_balance`, `get_mapping_taxonomy`, `submit_mapping` (staging — preparer confirms), `get_prior_mappings`, `search_knowledge`.
- **Memory:** working; episodic per entity (chart-of-accounts stability means prior confirmed mappings are the strongest prior — reused as *suggestions* with provenance, re-confirmed each period).
- **Prompt core:** *"You map financial statement lines to the tax computation taxonomy. Prior confirmed mappings are suggestions, not facts — flag any account whose usage pattern changed. Unmappable or ambiguous lines are escalated with candidates, never forced. Movement commentary references the actual figures by line ref."*
- **I/O:** `TaskEnvelope{context: tb_ref, taxonomy_version}` → `MappingProposal{mappings[{line, target, confidence, basis}], unmapped[], movements[], flags[]}`.
- **Error/escalation:** taxonomy-version mismatch vs pack ⇒ block + P5; low aggregate mapping confidence ⇒ route whole proposal to preparer review rather than piecemeal.
- **Evaluation:** mapping accuracy vs confirmed ground truth (≥95% on stable charts, measured per period); unmapped-discipline (0 forced mappings on golden ambiguous lines); prior-mapping drift detection (seeded usage changes caught ≥90%); preparer correction rate (trend).

---

## 4.8 Registry summary (full roster)

| Agent | Template | Release | Model route | Confidence threshold |
|---|---|---|---|---|
| Supervisor | — | R1 | reasoning | n/a (plans validated mechanically) |
| Data | — | R1 | standard | 0.9 |
| VAT | tax_domain | R1 | standard | 0.85 |
| Fraud | — | R1 | standard | 0.85 |
| Reporting | — | R1 | standard | 0.9 |
| Critic | — | R1 (basic) / R2 (full) | reasoning | n/a (verdicts, not confidence) |
| Research | — | R2 | standard | GROUNDED ≥0.9 |
| Document | — | R2 | fast (extract) + standard (classify) | field-level |
| Corporate Tax | tax_domain | R2 | reasoning | 0.85 |
| Risk | — | R2 | reasoning | 0.85 |
| Financial Statement | — | R2/R3 | standard | 0.85 |
| Regulatory Monitor | — | R3 | standard | relevance-recall-tuned |
| Audit Readiness | — | R3 | standard | n/a (checklist-mechanical) |
| WHT / TP | tax_domain | R4 | standard / reasoning | 0.85 |
