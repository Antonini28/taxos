# 01 — Design System ("Meridian" design language)

Tokens are the single source of truth: defined as CSS custom properties, mirrored into Tailwind config, consumed by shadcn component theming. **No raw hex/px in feature code** — lint rule (`tailwindcss/no-arbitrary-value` allow-list) enforces token usage.

## 1. Color system

### 1.1 Neutrals & surfaces (UI chrome)

Slate-neutral scale (cool gray, Linear/Vercel register). Both modes are **selected designs** — dark is its own tuned scale, not an inversion.

| Token | Light | Dark | Use |
|---|---|---|---|
| `bg-page` | `#f9f9f7` | `#0d0d0d` | App background plane |
| `bg-surface` | `#fcfcfb` | `#1a1a19` | Cards, panels, tables, charts |
| `bg-surface-2` | `#f3f2ef` | `#232322` | Nested/inset surfaces, code, table headers |
| `bg-overlay` | `#ffffff` | `#232322` | Popovers, modals, command palette |
| `ink-primary` | `#0b0b0b` | `#ffffff` | Headings, primary values |
| `ink-secondary` | `#52514e` | `#c3c2b7` | Body, labels |
| `ink-muted` | `#898781` | `#898781` | Metadata, axis labels, placeholders |
| `border-hairline` | `rgba(11,11,11,.10)` | `rgba(255,255,255,.10)` | Card rings, dividers |
| `border-strong` | `#c3c2b7` | `#383835` | Inputs, emphasis borders |

### 1.2 Brand & interaction

| Token | Light | Dark | Use |
|---|---|---|---|
| `accent` | `#2a78d6` | `#3987e5` | Primary actions, links, active nav, focus ring base |
| `accent-hover` | `#1c5cab` | `#5598e7` | Hover states |
| `accent-subtle` | `#cde2fb` @ 40% | `#184f95` @ 30% | Selected rows, active-tab washes |
| `focus-ring` | 2px `accent` + 2px offset | same | Every focusable element, no exceptions |

One accent. Enterprise credibility dies by rainbow — emphasis comes from type scale and space, not extra hues (D1).

### 1.3 Status system (fixed, never themed, never used for series)

| Token | Hex (both modes) | Pairing rule |
|---|---|---|
| `status-good` | `#0ca30c` | Always icon (`circle-check`) + label |
| `status-warning` | `#fab219` | icon (`triangle-alert`) + label |
| `status-serious` | `#ec835a` | icon (`octagon-alert`) + label |
| `status-critical` | `#d03b3b` | icon (`octagon-x`) + label |

Compliance RAG statuses map: GREEN→good, AMBER→warning, RED→critical (serious = escalating band between). Status color **never** carries meaning alone (icon + text always — WCAG 1.4.1) and never appears as a chart series color.

### 1.4 Data-visualization palette (machine-validated)

Adopted from a CVD-validated reference set (adjacent-pair colorblind ΔE ≥ 8 target and normal-vision floor pass in **both** modes; validation is re-run in CI by `validate_palette.js` whenever tokens change — chart colors are computed-safe, not eyeballed):

| Series slot | Light | Dark |
|---|---|---|
| 1 blue | `#2a78d6` | `#3987e5` |
| 2 green | `#008300` | `#008300` |
| 3 magenta | `#e87ba4` | `#d55181` |
| 4 yellow | `#eda100` | `#c98500` |
| 5 aqua | `#1baf7a` | `#199e70` |
| 6 orange | `#eb6834` | `#d95926` |
| 7 violet | `#4a3aa7` | `#9085e9` |
| 8 red | `#e34948` | `#e66767` |

Dataviz rules (binding on every chart; enforced by the shared chart wrappers, doc 05 §6):
- Slots assigned in fixed order per *entity*, never cycled or repainted when filters change series count; >8 series folds to "Other" or facets; scatter/heatmap forms cap at 4 slots (all-pairs validation limit) with direct labels.
- **One axis, always** — two measures of different scale = two charts or indexed series, never dual-axis.
- Sequential = blue ramp light→dark; diverging = blue↔red with neutral gray midpoint (variance vs prior period, forecast error); never rainbow.
- Marks: 2px lines, 4px rounded bar-ends (baseline-anchored), ≥8px points, 2px surface gaps between stacked/adjacent fills; grid = hairline; text in ink tokens, never series color.
- Hover layer by default: crosshair + tooltip (line/area), per-mark tooltip (bar/cell); every chart offers a table view (accessibility + export parity).
- Three light-mode slots (magenta/yellow/aqua) are sub-3:1 on surface by design → charts using them ship visible direct labels or legend + table (the relief rule).

## 2. Typography

| Token | Spec | Use |
|---|---|---|
| Family | **Inter** (self-hosted, `font-display: swap`), system-ui fallback; `tabular-nums` on all data columns/tickers | One family; weight does the work |
| `text-display` | 28/36, 650 | Page titles (rare) |
| `text-title` | 20/28, 600 | Section/card titles |
| `text-heading` | 16/24, 600 | Panel headers, table groups |
| `text-body` | 14/20, 450 | Default UI text |
| `text-small` | 13/18, 450 | Dense tables, metadata |
| `text-micro` | 11/16, 500, +2% tracking, uppercase optional | Overlines, column headers, badges |
| `text-hero` | 32/38, 650, tabular | KPI values |
| `text-code` | 13/20 mono (JetBrains Mono) | IDs, hashes, JSON |

14px body is the enterprise-density anchor (Azure/Linear convention). Minimum text size anywhere: 11px; minimum contrast: 4.5:1 body, 3:1 large/graphical (checked in CI via axe).

## 3. Spacing, radius, elevation

- **Spacing:** 4px base grid — `1=4 … 2=8, 3=12, 4=16, 6=24, 8=32, 12=48, 16=64`. Card padding 16; page gutters 24 (desktop) / 16 (tablet) / 12 (mobile); section gaps 24; dense-table row height 36, comfortable 44.
- **Radius:** `sm 4` (inputs, badges), `md 6` (buttons, cards), `lg 10` (modals, popovers), `full` (avatars, pills). Nothing else.
- **Elevation:** flat-first (borders over shadows, D1). `e0` none+hairline (cards); `e1` `0 1px 2px rgba(0,0,0,.06)` (dropdowns); `e2` `0 4px 16px rgba(0,0,0,.10)` (modals, command palette); `e3` drawer/right-panel shadow. Dark mode: elevation via surface lightening (`bg-overlay`), shadows nearly invisible by design.

## 4. Motion (Framer Motion presets — the only allowed animations)

| Preset | Spec | Use |
|---|---|---|
| `fade-in` | 120ms ease-out opacity | Tooltips, popovers |
| `slide-panel` | 200ms cubic-bezier(.32,.72,.24,1) translateX | Right rail, drawers |
| `expand` | 160ms height+opacity | Accordions, row expansion |
| `list-stagger` | 30ms/item, cap 8 items | Dashboard card entrance (first load only) |
| `pulse-live` | 2s subtle opacity loop | Live/streaming indicators only |
| `count-up` | 400ms on first paint only | KPI values (never on refetch — numbers must not "dance") |

Rules: nothing moves that didn't change; no parallax, no perpetual animation except `pulse-live`; `prefers-reduced-motion` collapses everything to instant + opacity; layout shift budget 0 (skeletons reserve exact space).

## 5. Iconography

**Lucide** exclusively, 16px default / 20px navigation, 1.5px stroke, `ink-secondary` default. Domain glyph registry (one icon per concept, used everywhere): entity `building-2`, obligation `calendar-clock`, batch `database`, computation `calculator`, anomaly `flag`, agent `bot`, approval `stamp`, evidence `file-check-2`, citation `quote`, audit `scroll-text`, knowledge `library`, risk `shield-alert`. Icons never appear without accessible names (`aria-hidden` + text, or `aria-label`).

## 6. Component inventory (shadcn base ⊕ TaxOS composites)

**Primitives (shadcn/Radix, tokenized):** Button (primary/secondary/ghost/destructive/link · sm/md · loading state built-in), Input, Select, Combobox, DatePicker/RangePicker, Checkbox, RadioGroup, Switch, Textarea, Dialog, Drawer, Popover, Tooltip, DropdownMenu, ContextMenu, Tabs, Accordion, Breadcrumbs, Toast (sonner), Skeleton, Badge, Avatar, Progress, Separator, ScrollArea, Command (⌘K palette), Form (RHF+Zod wired).

**TaxOS composites (the product's vocabulary — each with defined loading/empty/error/success states):**

| Component | Purpose / notes |
|---|---|
| `AppShell` | Left nav (collapsible 240→64px), top bar (tenant/entity switcher, search trigger, notifications, user), right context rail (contextual, 360px) |
| `PageHeader` | Breadcrumbs + title + `as_of` freshness chip + primary actions row |
| `KpiTile` | Hero value (count-up), delta chip (▲▼ + `status-*` semantics), sparkline, drill-down affordance — the only place numbers are large |
| `ChartCard` | Title, filter slot, chart region, table-view toggle, export menu (PNG/CSV), `as_of` chip, legend (always for ≥2 series) |
| `DataTable` | TanStack: server pagination (cursor), column pinning/resize/visibility, sort, row selection, saved views, density toggle, sticky header, keyboard grid navigation, CSV export, URL-synced state |
| `FilterBar` | One row above content: entity/period/status combos + date-range presets + free-text; chips for active filters; saved filter sets |
| `StatusBadge` | RAG/workflow states: icon + label + tooltip with state definition (never color alone) |
| `WorkflowStateBar` | Horizontal state machine strip (Draft → Prepared → Review → Approved) with actor+timestamp per node |
| `LineageSheet` | The D2 component: side sheet showing figure → computation lines → contributing transactions → source batch, each level linkable |
| `CitationChip` / `CitationPanel` | Inline chip (source code, e.g. "VIT13500") → panel with quote, ancestry, validity window, authority rank, outbound link |
| `ConfidenceIndicator` | Basis-aware (DETERMINISTIC ✓ / GROUNDED n% / JUDGEMENT n%) with explainer popover — never a bare percentage |
| `AgentTimeline` | Multi-agent run visualization: plan steps, live status, per-step cost/duration, expandable reasoning traces & tool calls |
| `ApprovalCard` | Content summary + content-hash chip + SoD-aware action row + comment; disabled states explain *why* (e.g. "you prepared this item") |
| `AnomalyCaseCard` | Pattern, materiality, SHAP explanation list (plain-language), prior dispositions, action row |
| `ShapBar` | Signed contribution bars (diverging pair), plain-language labels, model-version footnote |
| `DocViewer` | PDF/image render, extraction overlays (bounding boxes ↔ field list two-way highlight), zoom/rotate, page thumbs |
| `DiffView` | Side-by-side or inline (regulatory changes, version history) |
| `AuditTrailList` | Actor (human/agent chip) + action + before/after + hash-verified tick; virtualized |
| `EmptyState` | Illustration-free: icon, one sentence, one action (D1 — no cartoon mascots) |
| `ErrorState` | Problem-details aware: title, trace_id (copyable), retry, support link |
| `NotificationCenter` | Grouped by type, read state, deep links, mute rules per type |
| `CommandPalette` | ⌘K: navigate, entities, work items, actions ("approve…", "run agent…"), recent |
| `TenantSwitcher` | P6: tenant + entity scope, isolation-boundary styled (distinct border treatment — you always know whose data you see) |

## 7. Interaction standards

- **Keyboard:** every interactive element tabbable in DOM order; roving tabindex in grids/menus; `⌘K` palette; `g` then `d/w/a/r` nav chords; `?` shortcut sheet; Esc closes topmost layer; focus visibly returns after dialogs close.
- **Forms:** RHF + Zod schemas generated from `taxos_contracts` (one validation truth); inline errors on blur, summary on submit; dirty-state guard on navigation; autosave drafts where domain allows (notes, dispositions).
- **Feedback:** optimistic UI only for reversible actions (read-state, filters); server-confirmed for anything audited (approvals, dispositions) with button-level pending state; toasts for background completions (deep-linked); destructive actions = typed confirmation (entity name) — matching backend irreversibility semantics.
- **Density:** user-level density toggle (comfortable/dense) persisted; tables default dense for Analysts, comfortable for executive views.

## 8. Accessibility standard (WCAG 2.2 AA — CI-enforced)

axe-core in component tests + Playwright page scans (doc 05 §7); focus-visible on everything; target size ≥ 24px (2.2 AA 2.5.8); no keyboard traps (2.1.2); charts: table-view parity + text summaries (`aria-describedby`); live regions for agent-run updates (`aria-live="polite"`, status changes announced); modals: focus trap + `aria-modal` + labelled; color rules per §1; motion per §4; language: `lang` attrs, no all-caps in DOM text (CSS transform only).
