# CV Bullets & Interview Bank

## 1. CV bullets (pick 3–4 per application; tailor set to the role)

**AI Engineer / ML Engineer:**
- Designed and built TaxOS, an enterprise multi-agent AI platform (LangGraph, Azure OpenAI, FastAPI, PostgreSQL) automating the UK VAT compliance lifecycle end-to-end under human-approval governance, documented across 18 Architecture Decision Records.
- Engineered a governed agent runtime — capability-confined Tool Gateway, typed envelopes, run budgets, checkpointed escalation — with a CI-gated evaluation harness (golden datasets, mechanical invariants, LLM-judge with drift audit) blocking prompt/model regressions at merge.
- Built an explainable fraud/anomaly estate for cold-start conditions: rules + per-population Isolation Forests stacking to LightGBM ranking as reviewer dispositions accumulate labels; TreeSHAP explanations stored at scoring time; MLflow registry with human-gated production promotion.
- Implemented enterprise RAG with typed, mechanically-resolved citations (hybrid pgvector+BM25 retrieval, RRF fusion, cross-encoder reranking) achieving a ≥95% citation-support release gate and first-class "insufficient sources" refusals.

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
