# ADR-013 — LangGraph as the agent orchestration framework

**Status:** Accepted · 2026-07-20 · Principles: AP-2, AP-4; FR-301/302/303/305/306 · Builds on: ADR-012

## Context
Phase 3 requires selecting among LangGraph, CrewAI, and Microsoft AutoGen for the taxos-agents runtime. ADR-012 fixed the containment seams (Tool Gateway, typed envelopes, RunTracer, framework state never the system of record), making this a reversible decision to be optimised for fit, not hedged into paralysis. Full weighted evaluation: `docs/ai/01-framework-evaluation.md`.

## Decision
Adopt **LangGraph**: agent workflows as explicit typed state graphs; Postgres checkpointer for durable run state (pause/resume across days and deploys); `interrupt` primitives for human gates and escalations; nodes for LLM steps, deterministic functions, and tool calls; per-node streaming bridged to WebSocket run views and OTel spans.

## Alternatives
- **CrewAI** — best prototyping ergonomics; rejected: emergent/delegative control flow resists the bounded, enumerable execution paths our evidence model requires (weighted 2.3/5 vs 4.6/5).
- **Microsoft AutoGen / Agent Framework** — conversation-centric collaboration we deliberately prohibit (doc 10 §6); API surface in transition during the AutoGen→Agent Framework convergence; Azure alignment noted as a future re-evaluation trigger (2.8/5).
- **No framework (hand-rolled state machine)** — seriously considered given ADR-012 already owns the contracts; rejected because checkpointing, interrupt/resume, streaming, and provider abstraction are commodity plumbing LangGraph provides tested — we'd re-implement ~2k lines of undifferentiated risk.

## Consequences
- (+) Plans are reviewable artifacts: every possible path visible in the graph definition; loop bounds are structural (FR-305's max-2 critic loops is an edge condition, not a prompt instruction).
- (+) Durable gates: a run parked on `EscalationRaised` survives restarts and resumes in place (FR-306).
- (+) Hiring-market legibility: the dominant production framework — the portfolio goal served.
- (−) LangChain-ecosystem version churn → pins + lockfile, adapter layer, contract tests on the envelope boundary; upgrades are deliberate PRs.
- (−) Graph rigidity vs free agent improvisation → accepted on purpose: improvisation is the failure mode in a compliance domain. Novel situations route to escalation, not creativity.
- Re-evaluation triggers recorded: Microsoft Agent Framework API stability with concrete Azure payoff; LangGraph stewardship/licensing change; envelope contract proving insufficient for a required pattern.
