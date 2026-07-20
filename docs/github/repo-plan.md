# Phase 12 — Repository Plan

The meta-files (`.github/`, SECURITY.md, CONTRIBUTING.md, workflows) are authored and in place. This document covers what can only be executed at publish time: history strategy, repo settings, wiki, and visual assets.

## 1. Publish sequence (`Antonini28/taxos`)

```
1. git init + initial commit series (see §2 — NOT one "initial commit" blob)
2. Create private repo → push → verify Actions run green (workflows are already committed)
3. Repo settings per §3 (branch protection, environments, features)
4. Visual assets pass (§5) → README image links go live
5. Flip to public when R1 code exists to match the docs (docs-only public is acceptable
   earlier if labelled "design-complete, build in progress" in the README status line)
```

## 2. Commit history strategy ("meaningful commits" is a portfolio requirement)

The history should read like the build actually happened — because it did, in phases. Initial series mirrors the phase structure, then trunk-based development takes over:

```
docs: product discovery — problem, market, personas, requirements, roadmap (Phase 1)
docs: enterprise architecture — C4 models, cross-cutting concerns, ADR-001..012 (Phase 2)
docs: AI architecture — framework evaluation (ADR-013), agent catalogue, eval framework (Phase 3)
docs: knowledge management — corpus governance, retrieval, citations (ADR-014/015) (Phase 4)
docs: ML estate — anomaly detection, supervised models, MLOps (ADR-016/017) (Phase 5)
docs: backend engineering standards — audited UoW, invariant suite, local dev (Phase 6)
docs: frontend design package — Meridian design system, IA, flagship specs (Phase 7)
docs: cloud deployment — Terraform estate, K8s target, operations (ADR-018) (Phase 8)
docs: security programme — threat model, injection catalogue, compliance mappings (Phase 9)
docs: testing programme — performance suites, golden journeys, quality gates (Phase 10)
docs: documentation layer — README, portal, guides, business case (Phase 11)
chore: repository meta — workflows, templates, policies (Phase 12)
--- build commits follow trunk-based with Conventional Commits ---
feat(platform): monorepo skeleton, compose stack, CI green (US-101)
feat(masterdata): entities, jurisdictions, calendars (US-104)
feat(ingestion): batch upload + validation + quarantine (US-201) …
```

Rules once building: one story/concern per commit where practical · squash-merge PRs so `main` history = reviewed units · no "wip"/"fix typo" on main, ever · commit messages reference story IDs (US-xxx) — traceability from Phase 1 backlog to code, in `git log`.

## 3. Repository settings (applied at publish)

| Setting | Value |
|---|---|
| Branch protection `main` | PRs required, 0 stale approvals dismissed (solo) but **required status checks = the full PR workflow**, linear history, force-push blocked, admins included |
| Environments | `staging` (no reviewers), `prod` (required reviewer: owner) — matches main.yml |
| Actions | OIDC vars per environment (`AZURE_CLIENT_ID_*`); no repo-level cloud secrets |
| Features | Issues ✔ (templates committed) · Discussions ✔ (Q&A + Ideas categories) · Wiki ✔ (§4) · Projects: one board, release-train columns |
| Security | Private vulnerability reporting ✔ · Dependabot (weekly, grouped) ✔ · CodeQL (nightly workflow) · secret-scanning + push protection ✔ |
| Merge | Squash only; PR title → commit title (Conventional Commit lint on titles) |
| Labels | `triage`, area labels matching bug-template dropdown, `good-first-issue`, `security`, `regression`, `nightly`, `release-train:R1..R4` |

## 4. Wiki plan (thin by design)

The wiki **links, never duplicates** (drift rule from docs/README.md). Pages: Home (project map + quick links) · Screenshots gallery (per flagship screen, light+dark) · Demo script (the 3-minute walkthrough, presenter notes) · FAQ (build-vs-buy, why-not-X answers drawn from ADR alternatives sections) · Release notes (generated per train). Everything else redirects to `docs/`.

## 5. Visual assets plan (`docs/assets/`)

| Asset | Source | Used in |
|---|---|---|
| `architecture-hero.png` | The 60-second diagram, rendered from Mermaid with Meridian tokens (dark + light) | README, landing page, deck slide 10 |
| `screens/*.png` | Playwright visual-regression baselines double as marketing screenshots (deliberate reuse — they're pixel-true and always current) | README gallery link, wiki, deck |
| `demo.gif` | Scripted from `just demo`: instruct → plan → escalation → handoff → approve → evidence pack, ~25s, 1280px, <8MB (GIF) + `demo.mp4` (higher fidelity, linked) | README top |
| `evidence-pack-sample.pdf` | Generated from seeded data, redaction-checked | Deck appendix A3, wiki |
| Social preview image | Hero screenshot + wordmark, 1280×640 | Repo settings |

Asset rule: every image is regenerable by script (`just assets`) — screenshots and diagrams that can't be regenerated rot like hand-edited fixtures.

## 6. Badges (README top — kept honest)

CI (Actions status, live) · coverage (uploaded artifact → shields endpoint) · CodeQL · licence · Python/TypeScript versions · `docs: 11 phases` (static, links portal) · `ADRs: 18` (static, links log). Rule: no badge for a thing that isn't real and current — a red badge is information; a fake green one is a credibility bug.
