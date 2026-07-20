# Architecture Walkthrough — the 30-minute talk

**Audiences:** interview panel (primary) · conference/meetup (secondary). Structure: 6 chapters × ~5 min, each ending on a decision + trade-off (the interviewer's follow-up hooks are deliberate). Slides = diagrams already in the corpus; speak, don't read.

## Ch.1 — The problem shapes the architecture (0–5)
Tax compliance is high-volume data engineering with legal consequences: the quality drivers are auditability, correctness, governed autonomy, tenant isolation — *in that order*, and ranked before any technology talk. Show the drivers table (Phase 2 doc 01). **Decision hook:** "every architecture review I ran started with 'which driver does this serve' — and several exciting technologies lost to that question."

## Ch.2 — Right-sized services (5–10)
The 60-second diagram. Modular monolith core + isolated agent runtime + workers (ADR-001): the audit/state/outbox transaction *demands* one database transaction — distributed systems make the core guarantee harder, so the boundary criterion is a genuinely different runtime concern (scaling profile, dependency set, blast radius). Agents qualify; "vat-service vs ct-service" doesn't. **Trade-off:** whole-core release coupling, accepted with extraction-ready seams; graduation triggers named.

## Ch.3 — The trust machinery (10–16) — *the centrepiece*
Walk one write: `ApprovalService.grant` → SoD policy → content-hash check → AuditedUoW → chain-hashed audit event + outbox event, one commit. Then the three enforcement layers under it (lint bans raw commits; DB revokes UPDATE; CI invariant tests) and the WORM anchoring that bounds insider tampering. Then AP-2: LLMs never calculate — signed content packs, decimal-only engine, property-tested reproducibility. **Line that lands:** "the audit trail isn't a log we write — it's a transaction we can't avoid."

## Ch.4 — Agents you can let near a tax return (16–22)
The run state machine: bounded plans, budgets, escalation-not-guessing, HANDOFF terminal — *no edge to approval exists in the graph*. Tool Gateway: capability confinement enforced server-side, then again at IAM (agent identity has no business-storage access), then at network policy. Prompt injection assumed to *succeed* at the model layer — containment is what tools exist, what scopes bind, what schemas validate, what citations resolve, what humans gate. Evals as release gates: prompt changes that regress golden sets don't merge. **Framework note:** LangGraph won on governance-shaped criteria (4.6 vs 2.8/2.3) — and ADR-012 made the choice reversible before it was made.

## Ch.5 — ML with honest labels (22–26)
The cold-start ladder: rules → per-population Isolation Forest → dispositions become labels → supervised ranking stacks on top (never replaces — novel-pattern insurance). Thresholds from reviewer alert budgets, not ROC vanity. TreeSHAP-only, stored at scoring time ("you can't re-derive an explanation after the model moves"). Registry promotion requires human approval — a model going live is a state change of record. **Contrarian hook:** "we rejected LIME, autoencoders-at-MVP, XGBoost, Kafka, Neo4j-day-one, and GraphQL — each with a written trigger for revisiting. Restraint with receipts."

## Ch.6 — Proving it (26–30)
The invariant suite (architecture as executable tests — name three: unaudited-mutation-cannot-commit, cross-tenant-zero-rows, tool-gateway-has-no-approval-surface). Injection suite scoring *containment per layer*. Perf evidence from prod-shaped ephemeral environments. Release BOM: "what exactly is running" is a queryable fact. Close: "18 ADRs, 11 documentation phases, and every guarantee in this talk has a test with its name on it. Questions — the ADR log probably has a chapter on whichever one you pick."

## Q&A preparation
The likely challenges and where the answers live: *Why not microservices/Kafka/AKS from day one?* → ADR-001/003/008 alternatives sections. *What breaks first at scale?* → capacity statement + scale path (data doc §7). *How do you know the AI is right?* → confidence-with-basis + eval thresholds + the human gate ("we don't claim right — we claim evidenced-or-escalated"). *What would you do differently?* → honest answer prepared: earlier build-out of the vertical slice alongside design; the phase discipline traded early running code for decision quality — defensible, but say it before they do.
