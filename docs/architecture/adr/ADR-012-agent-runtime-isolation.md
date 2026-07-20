# ADR-012 — Agent runtime as isolated service behind a Tool Gateway (framework-agnostic seam)

**Status:** Accepted · 2026-07-20 · Principles: AP-2, AP-4, AP-5; FR-301/302/303, GP-1

## Context
Agents are the platform's differentiator and its riskiest surface (prompt injection, tool misuse, cost runaway, non-determinism). The framework choice (LangGraph vs CrewAI vs AutoGen) belongs to Phase 3, but the *architectural containment* of whatever framework wins must be fixed now, or the framework's abstractions will leak into the core and make the choice irreversible.

## Decision
1. **Separate deployable (`taxos-agents`)** with its own service identity; its database account has zero grants on business tables — run/step/memory tables only.
2. **All business access via the Tool Gateway** (`/tool-gateway/v1/*` on taxos-api): a small, enumerated, independently versioned API surface. Approval, filing, user-management, and audit-write endpoints do not exist on it. Per-agent tool grants are declared in registry config and verified server-side on every call (client-side allow-list is convenience; server-side is the control).
3. **Typed envelope contract** for supervisor↔agent communication (goal, context refs, budget, deadline / result, confidence, citations, cost) defined in the shared `contracts` package — the framework must be adapted to the envelope, never the reverse.
4. **Run governance in the runtime:** per-run budgets (tokens, tool calls, wall clock), bounded plans, capped critic loops, mandatory RunTracer persistence (a step that can't be traced can't execute).

## Alternatives considered
1. **Agents in-process with the core API** — simplest, but: LLM SDKs enter the AP-2-clean codebase, a prompt-injected agent shares memory space with approval logic, agent bursts scale the whole API, and framework lock-in becomes total. Rejected on all four.
2. **Agents with direct DB access (fast tools)** — performance appeal, catastrophic governance: RLS wouldn't distinguish agent intent, tool-level authorisation vanishes, and every agent bug becomes a data-integrity incident. The Tool Gateway is the enforcement point that makes FR-303 architectural rather than behavioural.
3. **One service per agent** — maximal isolation, absurd ops overhead for agents that are prompts + tool grants, not distinct runtimes. The registry pattern gives per-agent identity/limits inside one service; extraction remains possible if an agent ever needs a distinct runtime (e.g. GPU OCR).
4. **Framework-native everything (adopt LangGraph state/checkpointing as the system of record for runs)** — couples evidence (FR-302) to a fast-moving OSS schema; instead, framework state is internal and the RunTracer projects into *our* stable `agent_run/agent_step` schema.

## Consequences
- (+) Phase 3's framework decision (ADR-013) is genuinely two-way-door: the envelope + gateway + tracer survive a swap.
- (+) Security review of "what can agents do" = reading one route file + one grants config (enumerable, testable — the Phase 9 suite attacks exactly this surface).
- (+) Cost/blast-radius: scale-to-zero, provider circuit breakers, and kill-switch flag (`ff_agent_runs_enabled`) all land on one service.
- (−) Every new agent capability needs a gateway endpoint + grant + contract type (three artifacts) → deliberate friction, the same way approval gates are deliberate; template code-gen keeps it cheap.
- (−) HTTP hop on every tool call (~ms) vs in-process — negligible against LLM latencies (hundreds of ms–s).
