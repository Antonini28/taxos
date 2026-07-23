# CV Bullets & Interview Bank

> Refreshed 2026-07-23 to the BUILT system. Every claim below is verifiable in the repo —
> nothing here names a technology that exists only in the design docs. (Where the design
> specifies a production swap — LangGraph, LightGBM, MLflow, hybrid retrieval — say
> "designed", not "built", if you mention it at all.)

## 0. Flagship CV project entry (paste-ready, Selected AI Projects section)

**TaxOS — Enterprise Agentic Tax Operating System** (open source: github.com/Antonini28/taxos).
Governed multi-agent platform (Python, FastAPI, PostgreSQL, Next.js) carrying UK VAT **and**
Corporation Tax from ERP extract to review-ready, evidence-attached state: deterministic rule
engine with HMRC-cited per-figure lineage and tax types as data-driven content packs
(Corporation Tax added with zero engine changes); an architectural human-approval gate —
agent-callable approval endpoints do not exist; hash-chained audit trail with one-click
evidence packs; RAG that cites or refuses; and an explainable risk-ML ladder (exact Shapley
attributions; the supervised layer declines to train below a label floor). 169 tests against
real PostgreSQL in CI, 18 ADRs, runs locally in five minutes with no API keys.

## 1. CV bullets (pick 3–4 per application; tailor set to the role)

**AI Engineer / ML Engineer:**
- Built TaxOS, an open-source enterprise agentic tax platform (Python, FastAPI, PostgreSQL, Next.js): a multi-agent runtime prepares UK VAT and Corporation Tax end-to-end under an architectural human-approval gate — runs terminate in handoff, never approval, and the invariant is a named test. 169 tests against real PostgreSQL, CI-enforced; 18 ADRs.
- Proved "tax types are content, not code" by making it falsifiable: generalised the engine's derived-box arithmetic into a pack-declared formula evaluator (VAT output proven byte-identical via reproducibility hashes), then added Corporation Tax as a rule pack — same engine, lineage, approval gate and evidence pack, zero tax-specific pipeline code.
- Built an explainable risk-ML ladder for cold-start conditions: versioned rule detectors → a deterministic Isolation Forest whose every score carries an exact Shapley explanation (full coalition enumeration; contributions sum to the score) → a supervised GBM learning from reason-coded reviewer dispositions, excluding censored labels and refusing to train below a label floor with an evidenced INSUFFICIENT_LABELS verdict. Precision@10 = 100% on a labelled synthetic benchmark.
- Implemented grounded tax research with citation-or-refusal semantics: recall-first Postgres full-text retrieval, passages ranked by relevance then authority (legislation over guidance), and first-class evidenced INSUFFICIENT_SOURCES refusals — zero embeddings or API keys required to run.
- Engineered evidence-by-default: every mutation commits atomically with a hash-chained audit event; approvals bind to content hashes and void on data change; one click exports a self-contained evidence pack — figures, lineage, approvals, agent trace, and a fresh audit-chain verification.

**AI/Tax Technology Consultant:**
- Conceived and delivered a Big Four-standard internal-asset build: 13-phase programme from product discovery (market/gap analysis, personas, MoSCoW requirements) through architecture, security, and portfolio, with business case quantifying £0.8–2.2m annual value per client group.
- Designed compliance-grade AI governance adopted as architecture: deterministic tax computation (signed, citation-carrying rule packs; LLMs never calculate), hash-chained audit trails anchored to WORM storage, segregation-of-duties approval gates — mapped to ISO 27001, SOC 2, GDPR, and UK SAO/CCO obligations.
- Translated HMRC VAT rules into versioned rules-as-code content packs with per-rule citations, demonstrating the jurisdiction-as-content model that scales tax platforms without core engineering.

**Solutions Architect / Platform Engineer:**
- Architected a cloud-native Azure platform (Container Apps, PostgreSQL w/ RLS multi-tenancy, Service Bus, Key Vault, Terraform, GitHub Actions OIDC) with transactional-outbox eventing, zero stored credentials, and private-endpoint-only data plane; Helm/Kubernetes parity CI-validated on every PR.
- Established engineering governance as executable checks: import-linter module boundaries, an invariant test suite proving architectural guarantees (audit atomicity, tenant isolation, agent confinement), performance evidence from ephemeral prod-shaped environments, and release bills-of-materials.

## 2. Interview Q&A bank (the answers are rehearsal notes, not scripts)

**System design**

*Q: Design an AI system for a regulated workflow.* → Lead with quality drivers before tech; split deterministic core from probabilistic edge; enumerate agent capabilities as an API surface (delete, don't forbid); evidence in the write path; human gates as state-machine structure. TaxOS is the worked example — draw its 60-second diagram.

*Q: Monolith vs microservices?* → Boundary criterion = genuinely different runtime concern (scaling profile, dependency blast radius), not domain nouns. Core guarantee (audit+state+event atomicity) demanded one transaction → modular monolith with enforced module contracts, satellite services where criteria genuinely differed (agents). Extraction-ready seams; graduation triggers written down (ADR-001).

*Q: How do you scale it?* → Read the pressure, answer the layer: partitioning + async-first (in place) → caches/replicas → store swaps behind ports (pgvector→AI Search) → per-tenant databases. The capacity statement names the first bottleneck and its pre-designed response — scaling as maintained fact, not improvisation.

*Q: Multi-tenancy?* → Shared schema + RLS forced at the DB with transaction-local tenant config (the pooling pitfall), tenant-keyed caches, server-side WS filtering, storage path scoping — and the premium path (DB-per-tenant, same migrations) kept open. Verified by an attack suite plus canary rows; "provable isolation" is the selling phrase.

**AI engineering**

*Q: How do you stop hallucinations?* → Reframe: you don't stop them, you make them non-viable. Nine layers, but the three that matter: don't ask the model for facts (tools/engine supply them); schema-enforced attribution with mechanical citation resolution (invented refs fail to resolve → rejected pre-human); refusal as a first-class evidenced output. Then measure: citation-support rate is a CI gate.

*Q: Prompt injection?* → "We assume it succeeds." Then the containment stack: tools that don't exist, server-side scope from run context (never model output), structured outputs, budget caps, human gates — tested by a fixture catalogue scored by *which layer* caught each attack.

*Q: How do you evaluate agents?* → Weakest sufficient evaluator: mechanical invariants (free, absolute) → golden sets (CI-gated thresholds per agent) → LLM-judge (temperature-0, versioned, drift-audited against human agreement κ≥0.8) → sampled human audit. Prompt changes are code changes: no green evals, no merge.

*Q: When would you fine-tune?* → When retrieval + prompting demonstrably plateau on eval error analysis and the failure is vocabulary/format, not knowledge — not observed yet; embeddings fine-tune trigger is written in the docs. (Restraint with a trigger, again.)

**ML**

*Q: Fraud detection with no labels?* → The cold-start ladder, verbatim (rules → IF per population → dispositions-as-labels → supervised stack). Emphasise reason-coded dismissals: "not worth my time" is censored, not negative — the label-hygiene detail that separates practitioners from tutorials.

*Q: Why LightGBM over XGBoost? Why not deep tabular?* → Empirical frame: speed + native categoricals; CatBoost standing challenger where cardinality dominates; mandatory RF/logreg baselines that GBMs must beat by pre-registered margins; deep tabular has no evidence of lift at this scale and worse explainability. Champion/challenger makes it empirical per model, permanently.

*Q: Explainability — SHAP or LIME?* → TreeSHAP: exact for trees, deterministic, cheap. LIME's sampling instability is disqualifying for evidence (two explanations for one score = credibility incident). Deeper point: choose the model family for exact explainability rather than bolting approximators onto arbitrary models.

**Behavioural / judgement**

*Q: A decision you'd revisit?* → Phase discipline traded early running code for decision quality; I'd interleave the vertical-slice build sooner. Say it unprompted — it defuses the "it's all docs" challenge and demonstrates the self-review the ADRs institutionalise.

*Q: Biggest technical risk in the design?* → Honest answer: audit-chain write serialisation at the tenant tip (named in ADR-009, measured by a dedicated perf suite, mitigations sequenced). Naming your own weakest point with its test attached is the strongest answer in the deck.

## 3. Delivery notes

Every answer should end within 90 seconds and offer a doc: "the trade-off table is in ADR-00X" invites the follow-up you want. Bring the repo on screen; open the invariant test file when governance comes up — *showing* a test named `test_unaudited_mutation_cannot_commit` outperforms describing it.
