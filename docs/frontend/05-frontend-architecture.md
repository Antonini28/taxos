# 05 — Frontend Architecture (apps/frontend)

## 1. Application structure (Next.js App Router)

```
apps/frontend/src/
├── app/
│   ├── (auth)/login, mfa/                  # public segment, minimal shell
│   ├── (app)/                              # authenticated segment — AppShell layout
│   │   ├── layout.tsx                      # shell: nav, top bar, providers, WS boot
│   │   ├── dashboard/, tax/, agents/, fraud/, data/, documents/,
│   │   ├── knowledge/, work/, reports/, audit/, admin/, settings/
│   │   └── …/[id]/page.tsx                 # detail routes (server components fetch initial data)
│   └── api/auth/[...]/route.ts             # BFF token exchange endpoints only (no business proxying)
├── components/
│   ├── ui/                                 # shadcn primitives (generated, tokenized — do not hand-edit)
│   ├── composites/                         # doc 01 §6 inventory (KpiTile, DataTable, AgentTimeline…)
│   └── charts/                             # Recharts wrappers implementing dataviz rules (§6)
├── features/<domain>/                      # feature modules mirroring backend modules:
│   │                                       #   components/ hooks/ api.ts (generated client slice)
├── lib/                                    # api client core, ws client, auth, format (Money/date), utils
├── stores/                                 # Zustand: ui prefs, command palette, notification badge
├── styles/tokens.css                       # doc 01 tokens (light + dark blocks)
└── tests/                                  # unit/, e2e/ (Playwright), a11y/
```

Feature-module rule mirrors the backend: features import `components/*` and `lib/*`, never each other's internals (ESLint boundary rule — the frontend's import-linter).

## 2. Rendering & routing strategy

- **Server Components for first paint** of data-heavy pages (dashboard, lists): initial query executes server-side (SSR against the API with the user's session), streams HTML, then TanStack Query hydrates the same cache key client-side — fast TTFB *and* live interactivity, no double-fetch.
- Client Components for anything interactive (tables, charts, workspace); `"use client"` boundaries at composite level, not page level.
- Route groups per shell; loading.tsx = skeleton layouts (exact-space rule); error.tsx = segment error boundaries (§5).
- Code splitting: route-level automatic + deliberate dynamic imports for heavy payloads (DocViewer/pdf.js, Recharts bundle, DiffView) with skeleton fallbacks; Framer Motion via `LazyMotion` (domAnimation subset).
- Prefetch: nav links prefetch on viewport (Next default) + hover-prefetch for L2→L3 rows (TanStack `prefetchQuery` on row hover — the drill-down feels instant).

## 3. Data layer

- **Generated client:** `openapi-typescript` types + a thin typed fetch wrapper (`lib/api.ts`) — every response parsed against generated types; problem+json normalised to `ApiError {status, title, detail, traceId}`.
- **TanStack Query owns all server state.** Query keys = `[domain, resource, params]` convention; `staleTime` per data class: reference data 5m · lists 30s · aggregates 30s (with `as_of` shown) · workflow/approval state **0** (always revalidate — correctness class, mirrors ADR-011's never-cache list).
- **Mutations:** audited actions are never optimistic (button pending → server confirm → invalidate); reversible prefs are optimistic with rollback. Invalidation maps live beside mutations (`onSuccess: invalidate([...])`) and are the *frontend twin of the backend event-invalidation table*.
- **WebSocket integration:** one WS client (auto-reconnect w/ backoff + jitter, auth re-handshake); incoming events map to targeted `queryClient.invalidateQueries` / `setQueryData` patches + UI stores (badges, live strips). WS is enhancement: a `usePollingFallback` hook activates 30s polling per subscribed key when the socket is down (banner shows degraded-live state, D3).
- **Client state (Zustand):** UI-only — theme/density, palette open, nav collapse, unread counts. **No server data in Zustand, ever** (one cache, one truth).
- **URL state:** filters/tabs/table state via `nuqs`-style typed search params — shareable links are a feature requirement (doc 02 §2), so URL serialization is part of each list component's contract.

## 4. Authentication flow (BFF, Phase 2 doc 07)

Login → `/api/auth/login` (Next route) → OIDC redirect (PKCE) → callback exchanges code server-side → httpOnly SameSite=strict cookies (access 15m / rotating refresh) → middleware guards `(app)` segment (redirects to login, preserves deep link) → API calls carry the cookie; 401 triggers single-flight refresh then replay; refresh failure → session-expired dialog (preserves unsaved work in sessionStorage where forms opted in). Role/scope claims hydrate an `AuthzContext` provider — **UI gating only** (menus, affordances); the server remains the enforcer, and hidden-vs-disabled follows doc 02 §3 (Auditor sees no mutating affordances at all; SoD-blocked actions render disabled *with reasons*).

## 5. Error handling & resilience

| Layer | Behaviour |
|---|---|
| Segment error boundaries | Per route group: ErrorState card w/ trace_id + retry (re-render + refetch); root boundary = full-page fallback w/ support link |
| Query errors | Card/table-level ErrorStates (a failed aggregate never blanks a page — flagship rule); background refetch errors → toast only if data is stale beyond policy |
| Mutation errors | Problem-details mapped to field errors (422 w/ errors[]) via RHF `setError`; conflict (409/412) → refresh-and-reapply dialog; SoD (403 subtype) → explanatory inline card |
| Degraded modes | Global status store fed by WS/health: LLM circuit open, stub mode, stale aggregates → persistent banners (amber), never toasts |
| Crash telemetry | `window.onerror`/boundary reports → OTel browser SDK → App Insights (release-tagged, sourcemapped) |

## 6. Chart layer (`components/charts/`)

Recharts wrapped once: `<TrendChart>`, `<BarBreakdown>`, `<Waterfall>`, `<HeatGrid>`, `<Sparkline>`, `<ShapBars>` — features never import Recharts directly. Wrappers enforce the dataviz contract (doc 01 §1.4): token-fed series colors (fixed slot assignment by entity key), one axis, hover layer + tooltips, legend rules, table-view toggle (renders the same data as `DataTable`), export (PNG via html-to-image, CSV from source rows), `aria-describedby` auto-summary ("VAT liability, 6 quarters, trending up 8%"). Palette validation runs in CI against tokens (`validate_palette.js` both modes) — a token PR that breaks CVD separation fails the build.

## 7. Performance & quality budgets (CI-enforced)

- **Budgets:** initial JS ≤ 250KB gz per route (bundle-analyzer diff on PR); LCP ≤ 2.0s / INP ≤ 200ms / CLS = 0 (Lighthouse CI on flagship pages, throttled); table virtualisation beyond 100 rows (TanStack Virtual).
- **Testing pyramid:** component tests (Testing Library + axe per composite — every state in doc 01 §6 inventory gets a story + assertion); integration (MSW-mocked API against generated types — mock drift impossible); E2E (Playwright: the 6 golden journeys — login→dashboard→drill, upload→validate, instruct-agent→handoff, review→approve incl. SoD denial, anomaly→disposition, doc review→promote) run against compose stack in CI (stub-LLM mode); visual regression (Playwright screenshots, light+dark, flagship screens); a11y (axe in component tests + Playwright scans on all 28 routes, zero serious/critical violations gate).
- **Storybook** for the composite inventory (all states) — doubles as the design-system reference and the screenshot source for docs/portfolio.

## 8. Implementation order (post-approval)

1. Tokens + Tailwind config + shadcn theming + Storybook scaffold
2. AppShell, nav, auth flow, command palette
3. DataTable/FilterBar/ChartCard/KpiTile (the L2 kit) → Operations dashboard + VAT list (first vertical slice, real API)
4. Work item + ApprovalCard + LineageSheet (the L3 kit)
5. Agent workspace + AgentTimeline (WS layer)
6. Fraud centre → Executive dashboard (needs aggregates live) → remaining estate per release train
