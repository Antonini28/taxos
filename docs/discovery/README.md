# Phase 1 — Product Discovery

**Product:** Enterprise Agentic Tax Operating System (codename: **TaxOS**)
**Document owner:** Product & Architecture
**Status:** Complete — awaiting stakeholder review
**Last updated:** 2026-07-20

## Purpose

This discovery workspace establishes *why* TaxOS should exist, *who* it serves, and *what* it must do before a single architectural decision is made. Every artifact downstream (architecture, AI design, backlog grooming) traces back to a requirement or persona defined here. This mirrors the product discovery discipline used for internal asset builds at the Big Four (e.g., Deloitte's iDEA/Omnia, PwC's Sightline, KPMG's Digital Gateway).

## Artifact index

| # | Document | Contents |
|---|----------|----------|
| 01 | [Business Problem & Market Opportunity](01-business-problem-and-market.md) | Problem statement, cost-of-inaction, TAM/SAM/SOM, market drivers |
| 02 | [Competitive Landscape](02-competitive-landscape.md) | Competitor analysis, gap analysis, positioning |
| 03 | [User Personas](03-user-personas.md) | Six personas with goals, pains, and success measures |
| 04 | [Requirements](04-requirements.md) | Functional (FR) and non-functional (NFR) requirements, MoSCoW-prioritised |
| 05 | [Product Roadmap](05-roadmap.md) | Four release trains from MVP to enterprise GA |
| 06 | [User Stories & Backlog](06-user-stories-and-backlog.md) | Epics, user stories with acceptance criteria, prioritised backlog |
| 07 | [MVP & Enterprise Scope](07-mvp-and-enterprise-scope.md) | MVP cut line, enterprise edition definition, out-of-scope register |

## Traceability convention

- Requirements are numbered `FR-xxx` / `NFR-xxx` and are referenced by user stories (`US-xxx`) and later by Architecture Decision Records (`ADR-xxx`).
- Personas are referenced by code (`P1`–`P6`) in every user story.
- Nothing enters the backlog without a requirement and persona linkage — this is how scope creep is controlled.
