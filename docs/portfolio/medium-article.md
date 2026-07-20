# Medium Article (publish-ready)

**Title:** Agents You Can Let Near a Tax Return: Engineering Governed Autonomy
**Subtitle:** What it actually takes to put multi-agent AI inside a compliance workflow — architecture, not vibes
**Length:** ~1,600 words · **Audience:** engineers/architects · **Canonical link:** repo

---

Every agent demo follows the same arc: impressive autonomy, hand-waved governance. That ordering is exactly backwards for any domain where the output has legal consequences. I spent the last months designing TaxOS — an enterprise agentic platform for tax compliance — and the central lesson is that **the governance layer is the system**; the agents are almost the easy part.

This article walks the five design moves that made autonomy safe enough to be useful. All of it is public in the repo, including 18 ADRs recording the alternatives.

## Move 1: Split what must be right from what must be smart

Tax has a property most LLM applications don't: large parts of it are *deterministic law*. A VAT return is not a judgement call — it's arithmetic over classified transactions under versioned rules.

So the platform's first rule: **LLMs never calculate tax.** A pure-function engine (decimal arithmetic, no I/O, property-tested: same inputs + same rule version ⇒ byte-identical output) interprets signed *content packs* — data files carrying rates, box mappings, and effective dates, each rule citing the HMRC paragraph behind it. Agents trigger the engine as a tool and then do what LLMs are actually good at: explaining variances, flagging judgement areas, drafting narratives.

The structural trick that makes this stick: the draft-return schema **has no numeric fields** — only references into engine snapshots. An agent physically cannot author a figure. Guardrails you can grep for beat guardrails you prompt for.

## Move 2: Make dangerous actions impossible, not forbidden

Prompt injection defence usually means input sanitisation and hopeful system prompts. Useful — but the honest engineering position is that **injection sometimes succeeds at the model layer**, so the consequences must be bounded architecturally.

TaxOS agents run in a separate service whose database role has zero grants on business tables. Everything they do goes through a *Tool Gateway*: a small, enumerated API surface where every call is verified server-side against the agent's declared grants — and where approval, filing, and user-management endpoints **do not exist**. The same confinement repeats at the IAM layer (the agents' cloud identity can't touch business storage) and the network layer (policies allow agents → API and agents → LLM provider, nothing else).

The security suite scores injection fixtures by *which layer contained them* — because "the model refused" is luck, and luck is not a control.

## Move 3: Autonomy that stops is autonomy you can trust

Agent runs are LangGraph state machines with three properties worth stealing:

1. **No edge to approval.** The graph's terminal state is `AWAITING_HUMAN_REVIEW`. Approving requires a different human, verified by segregation-of-duties policy, binding their identity to a content hash of exactly what they reviewed. Change the inputs later and the approval voids — by hash mismatch, not by process.
2. **Escalate, never guess.** Missing payroll extract? The run parks with a card naming the gap, and resumes from a checkpoint when a human provides it. "I don't know" is a first-class state — in compliance, fabricated completeness is the worst failure mode there is.
3. **Budgets are graph state.** Tokens, tool calls, wall-clock — decremented per step, escalating on exhaustion. A looping agent throttles itself into a human's queue, not into a five-figure invoice.

Framework choice followed from these requirements, not vice versa: LangGraph won a weighted evaluation (bounded control flow, durable interrupts, Postgres checkpointing) over CrewAI and AutoGen — and an earlier ADR had already confined the framework behind typed envelopes so the choice stayed reversible.

## Move 4: Evidence as a write-path concern

Compliance platforms love the phrase "audit trail." Usually it means log statements. TaxOS makes it a transactional invariant: every business mutation commits **atomically** with a hash-chained audit event and a transactional-outbox event — one unit of work, one commit. An unaudited mutation isn't a bug that slips through; it's an exception (`UnauditedMutationError`) enforced by the only code path allowed to call `commit()` (lint-banned elsewhere), by database-level `REVOKE`s, and by a CI invariant test with exactly that name.

Chain heads anchor hourly to immutable (WORM) storage, so even a privileged insider rewriting the database breaks verification against the anchors. The payoff is a product feature: one click assembles an evidence pack — figures, lineage down to source transactions, approvals, agent traces, citations. "Audit-ready" stops being a quarterly panic and becomes a download.

The same philosophy runs through the AI layer. Citations are typed objects: source reference, verbatim quote, claim span, temporal validity. They resolve mechanically — the quote must be a substring of the stored source — before any human sees the output. A model that invents `VIT99999` doesn't produce a wrong answer; it produces a rejected one. And when retrieval can't support an answer, the system returns `INSUFFICIENT_SOURCES` *with diagnostics* — a refusal that is itself evidenced.

## Move 5: Boring ML, honestly labelled

Fraud detection in a cold-start world: you have zero labelled fraud on day one. The estate is a ladder — versioned rules (institutional knowledge as config), per-population Isolation Forests (population design *is* the model design; one global model would flag every large entity's normal as another's outlier), then reviewer dispositions accumulate as labels until a supervised ranker earns its activation gate. The unsupervised layers keep running afterwards: a supervised model only knows yesterday's fraud.

Two disciplines held throughout: **alert budgets, not ROC vanity** (thresholds set by reviewer capacity — an ignored queue is a failed model), and **TreeSHAP-only explainability, stored at scoring time** (approximate explainers like LIME are unstable, and you cannot faithfully re-derive an explanation after the model retrains; an evidence platform can't show an auditor two different explanations for one score).

## What I'd tell you to steal

If you're putting agents into any regulated workflow: (1) find your deterministic core and wall it off from the model; (2) enumerate agent capabilities as an API surface and delete the dangerous endpoints rather than forbidding them; (3) make refusal and escalation first-class outputs; (4) put audit in the transaction, not the logger; (5) gate prompt and model changes on evaluation suites like you gate code on tests.

None of this is exotic. All of it is deliberate. That's rather the point — *enterprise-grade agentic AI* is mostly the disciplined application of things we already knew, to a technology we're still learning to distrust correctly.

---

*The full corpus — architecture, agent specs, threat model, eval framework — is at github.com/Antonini28/taxos. It runs locally in five minutes, no API keys. I'm Olisa Anthony (MSc AI, ex-PwC Tax Technology); critique welcome.*
