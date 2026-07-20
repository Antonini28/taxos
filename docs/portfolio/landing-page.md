# Landing Page — Copy & Spec

**Implementation:** static page in the Next.js app (`/(marketing)` route group) or standalone Vercel deploy; Meridian tokens; light/dark; Lighthouse ≥95 all categories; one page, no nav maze.

---

## Hero

**H1:** Agents prepare. Humans decide. Everything is evidence.

**Sub:** TaxOS is an enterprise agentic AI platform for tax compliance — autonomous agents carry the work from ERP extract to review-ready state, on a deterministic computation core, with a cryptographic audit trail. Built to the standard of a Big Four internal asset.

**CTAs:** `View the code →` (GitHub) · `Watch the 3-minute demo` (video modal)
**Backdrop:** executive dashboard screenshot (dark), subtle parallax-free.
**Trust strip:** `18 ADRs` · `Deterministic tax engine` · `Human-gated approvals` · `WCAG 2.2 AA` · `Azure cloud-native`

## Section: The problem (two sentences, one stat bar)

Tax teams spend most of their capacity preparing data instead of exercising judgement, while regulators digitise faster than corporates respond. Compliance platforms automate forms and copilots answer questions — nobody ships the layer that *does the work under governance*.
Stat bar: `50–70% of tax-team time on data prep` · `£19bn tax-tech market` · `0 shipped governed-execution platforms`

## Section: How it works (the flagship flow, 5 steps with screenshots)

1. **Ingest & validate** — ERP extracts land, every row validated, failures quarantined with reasons.
2. **Agents execute** — a Supervisor plans; specialist agents compute (deterministically), investigate anomalies, and draft narratives with citations.
3. **Escalate, don't guess** — missing data parks the run and asks a human; nothing is fabricated.
4. **Humans approve** — evidence-first review: every figure drills to source, every claim cites, approval binds to a content hash.
5. **Evidence by default** — one click exports the pack: figures, lineage, approvals, agent traces, citations.

## Section: The four locks (differentiator grid)

| | |
|---|---|
| 🔒 **Agents cannot file** — approval endpoints don't exist on the agent surface; humans gate every state change | 🔢 **LLMs never calculate** — versioned, signed rule packs; bit-for-bit reproducible computation |
| 📎 **Cited or refused** — every tax claim resolves to a source passage, or the platform says "insufficient sources" | ⛓️ **Tamper-evident by design** — hash-chained audit log anchored to immutable storage |

## Section: Built like a product, documented like a platform

Three-column links with counts: **Architecture** (C4 models, 18 ADRs — "including the roads not taken") · **AI engineering** (13 agent specifications, eval harness with CI gates, injection catalogue) · **Operations** (Terraform estate, runbooks, quarterly DR rehearsals, performance evidence reports).
Below: the 60-second architecture diagram, theme-aware.

## Section: See it yourself

Terminal block: `git clone … && just up && just demo` — *"Five minutes to a working platform. No cloud account, no API keys — persona logins and a recorded agent run included."*

## Footer

Built by **Olisa Anthony** — MSc Artificial Intelligence · Software Engineering · ex-PwC Tax Technology. GitHub · LinkedIn · Email. Small print: portfolio reference platform; synthetic data; illustrative cited UK tax-rule subset.

---

**Design notes:** max-width 1100px; generous vertical rhythm (96px sections); screenshots in browser-chrome frames with hairline borders; no stock imagery, no illustrations — the product is the visual; motion limited to scroll-reveal fades (respecting reduced-motion); OG image = social preview from repo plan.
