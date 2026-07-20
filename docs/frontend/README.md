# Phase 7 — Frontend: Enterprise Product Design & Engineering

**Product:** Enterprise Agentic Tax Operating System (TaxOS)
**Status:** Complete design package — presented for review & approval before implementation (per stakeholder directive)
**Inputs:** Phase 1 personas & UI/UX requirements, Phase 2 API contracts & WebSocket design, Phase 3 agent run model, Phase 6 backend standards
**Last updated:** 2026-07-20

## Product design principles

| # | Principle | What it forbids |
|---|-----------|-----------------|
| D1 | **Calm density.** Enterprise users live here 6 hours a day: information-dense, chrome-light, generous whitespace *within* a disciplined grid (Linear/Stripe register, not marketing-site airiness) | Hero sections, oversized cards, dashboard-as-poster |
| D2 | **Evidence at every number.** Any figure on any screen drills to its lineage (Phase 2's lineage-as-data made visible) — the UI *is* the audit trail's front door | Dead-end KPIs, unexplained deltas |
| D3 | **State is always visible.** Workflow state, agent activity, data freshness (`as_of`), degraded modes (stub LLM, unreranked retrieval) are surfaced, never implied | Silent staleness, hidden queues |
| D4 | **AI is legible, not magical.** Confidence bases, citations, cost, and the human gate are permanent UI elements — trust is built by showing the machinery | Chat-bubble-only AI, unexplained scores |
| D5 | **Role-shaped, not role-locked.** One design system, per-role landing experiences and information hierarchy (Analyst → Partner); RBAC hides what you cannot do, the design decides what you see *first* | One-dashboard-fits-all |
| D6 | **Accessible by construction.** WCAG 2.2 AA, full keyboard model, validated color system (chart palette machine-validated for CVD in both modes) | Color-alone meaning, focus-invisible interactions |
| D7 | **Screenshot-grade always.** Every state — including empty, loading, and error — is designed; demo data is realistic; dark mode is a first-class selected design, not a filter | Lorem ipsum, unstyled edge states |

## Document map

| # | Document | Contents |
|---|----------|----------|
| 01 | [Design System](01-design-system.md) | Tokens (color/type/space/elevation/motion), dataviz standard, iconography, component inventory |
| 02 | [Information Architecture](02-information-architecture.md) | Sitemap, navigation model, role experiences, dashboard hierarchy, cross-cutting patterns |
| 03 | [Flagship Screen Specifications](03-flagship-screens.md) | Deep specs + wireframes: Executive Dashboard, AI Agent Workspace, Approvals & Workflow, Fraud & Risk Centre, Document Review |
| 04 | [Page Catalogue](04-page-catalogue.md) | Complete specifications for all remaining screens (28-page estate) |
| 05 | [Frontend Architecture](05-frontend-architecture.md) | Next.js structure, state/caching, auth flow, error boundaries, performance, testing |

## Stack (locked)

Next.js 14+ (App Router) · React 18+ · TypeScript strict · TailwindCSS · shadcn/ui (Radix primitives) · Framer Motion · TanStack Query + Table · React Hook Form + Zod · Recharts (wrapped) · Lucide icons · `next-themes` (dark mode) · Playwright + Testing Library + axe-core (testing)

## Review gate

Per the stakeholder directive, this package (IA, sitemap, navigation model, dashboard hierarchy, wireframes, component inventory) is presented **for approval before implementation begins**. Implementation order after approval: design-system primitives → app shell & navigation → flagship screens (R1 scope) → page estate per release train.
