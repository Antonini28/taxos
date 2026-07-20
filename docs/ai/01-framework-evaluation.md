# 01 — Agent Framework Evaluation: LangGraph vs CrewAI vs AutoGen

## 1. Evaluation frame

Because ADR-012 already isolated the framework behind the Tool Gateway + envelope contract + RunTracer, this is a **two-way-door decision** — but still consequential: the framework determines how naturally we express bounded plans, human-in-the-loop interrupts, and durable run state. Criteria are weighted by TaxOS's quality drivers, not by general popularity.

| # | Criterion | Weight | Why it matters here |
|---|---|---|---|
| C1 | Explicit, bounded control flow (auditable execution paths) | 25% | FR-302 replayability; a run must be a reviewable artifact, not an emergent conversation |
| C2 | Human-in-the-loop primitives (pause/resume, interrupts) | 20% | GP-1/FR-303: runs *end* at approval gates and *park* on escalation (FR-306) — first-class, not bolted on |
| C3 | Durable state / checkpointing to our store | 15% | Runs pause for days awaiting data; state must persist in Postgres, survive deploys |
| C4 | Streaming + observability hooks | 10% | Live run view (WS), OTel spans per step |
| C5 | Structured tool-calling maturity | 10% | Schema-validated outputs only (doc 07 §3 injection containment) |
| C6 | Production maturity & ecosystem trajectory | 10% | Big Four deployment credibility; hiring-market signal |
| C7 | Testability (unit-test a node/agent in isolation) | 10% | NFR-10; eval harness in CI |

## 2. Candidate assessment

### LangGraph (LangChain ecosystem)
Model: agents as **explicit state graphs** — typed shared state, nodes (LLM calls, tools, deterministic functions), conditional edges, cycles with bounds.
- C1 ★★★★★ The graph *is* the control flow; every possible path is enumerable at review time. Bounded loops are a graph property, not a prompt hope.
- C2 ★★★★★ `interrupt`/resume and checkpointer-based pauses are core primitives — pause-at-gate, park-on-escalation map 1:1.
- C3 ★★★★★ Pluggable checkpointers incl. Postgres — run state lands in our system of record next to `agent_run` (RunTracer projects from it).
- C4 ★★★★☆ Token/step streaming built in; callbacks map cleanly to OTel spans.
- C5 ★★★★☆ Structured output + tool binding mature across providers (Azure OpenAI included).
- C6 ★★★★☆ The current de facto production standard for controlled agent workflows; large talent pool; LangSmith optional (we use our own tracing — no lock-in).
- C7 ★★★★☆ Nodes are functions over typed state — unit-testable without LLM calls (mock the model, assert transitions).
- Risks: LangChain-ecosystem API churn (pin versions; our envelope adapter contains the blast radius); it's a library, not a runtime — we own execution (which ADR-012 wanted anyway).

### CrewAI
Model: role-based crews (role/goal/backstory), sequential or hierarchical processes; Flows add event-driven control.
- C1 ★★☆☆☆ Delegation and task ordering are framework-mediated and partly emergent; the executed path is harder to enumerate and bound. Flows improve this but re-implement graph control less maturely than LangGraph has it.
- C2 ★★☆☆☆ HITL exists (task-level human input) but pause-for-days-resume-in-place durability is not a first-class primitive.
- C3 ★★☆☆☆ Memory/state persistence exists; transactional Postgres checkpointing of arbitrary mid-graph state is not the design centre.
- C4 ★★★☆☆ C5 ★★★☆☆ Adequate. C6 ★★★☆☆ Strong adoption for rapid prototyping; thinner production-governance track record. C7 ★★☆☆☆ Role-prompt behaviour is tested end-to-end or not at all.
- Honest strength: fastest zero-to-demo; the role/goal ergonomics are genuinely pleasant. That is optimising for the part of the problem TaxOS finds easy.

### Microsoft AutoGen (0.4+, converging into Microsoft Agent Framework)
Model: **conversation-centric** multi-agent (agents message each other; group chats with orchestrator policies); 0.4 rebuilt on an async event-driven core; Microsoft has since folded AutoGen + Semantic Kernel into the **Agent Framework**.
- C1 ★★☆☆☆ Conversations are powerful for open-ended collaboration but our doc 10 §6 rule ("agents never message each other directly; typed envelopes via Supervisor") exists precisely because free conversation is untraceable and unbudgetable for compliance work. We'd spend our time suppressing the framework's native paradigm.
- C2 ★★★☆☆ Human-in-the-loop as a human proxy agent — workable, less crisp than graph interrupts for durable gates.
- C3 ★★★☆☆ State/serialization improved in 0.4; Postgres-native checkpointing is DIY.
- C4 ★★★☆☆ C5 ★★★★☆ (excellent on Azure OpenAI, unsurprisingly). C6 ★★★☆☆ Research pedigree + Microsoft alignment (a real Big Four optics point), but the AutoGen→Agent Framework transition makes the API surface a moving target this year. C7 ★★★☆☆.
- Honest strength: Azure-ecosystem alignment and the successor Agent Framework's enterprise trajectory — worth tracking as a future re-evaluation trigger, not adopting mid-migration.

## 3. Weighted scores

| Criterion (weight) | LangGraph | CrewAI | AutoGen |
|---|---|---|---|
| C1 Explicit control (25) | 5 | 2 | 2 |
| C2 HITL (20) | 5 | 2 | 3 |
| C3 Durable state (15) | 5 | 2 | 3 |
| C4 Streaming/obs (10) | 4 | 3 | 3 |
| C5 Tool calling (10) | 4 | 3 | 4 |
| C6 Maturity (10) | 4 | 3 | 3 |
| C7 Testability (10) | 4 | 2 | 3 |
| **Weighted /5** | **4.6** | **2.3** | **2.8** |

## 4. Recommendation

**LangGraph**, recorded as [ADR-013](../architecture/adr/ADR-013-langgraph.md). The decisive argument is qualitative, not the score: TaxOS's agent requirements are *governance-shaped* — bounded plans, durable pauses at human gates, enumerable execution paths, per-step evidence. LangGraph's graph-and-checkpoint model expresses these natively; the alternatives express them against the grain. CrewAI optimises prototype speed we don't need; AutoGen optimises emergent collaboration we deliberately forbid.

Containment (per ADR-012, restated as commitments): LangGraph state is internal — evidence lives in our `agent_run/agent_step` schema via RunTracer; the envelope contract stays framework-free; LangChain deps are pinned and confined to `taxos-agents`; re-evaluation trigger = Microsoft Agent Framework reaching API stability + a concrete Azure-integration payoff, or LangGraph licensing/stewardship change.
