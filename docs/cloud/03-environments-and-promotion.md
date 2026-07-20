# 03 — Environments & Promotion

## 1. Environment matrix

| | local | ci | staging | prod |
|---|---|---|---|---|
| Infra | compose (Phase 6 doc 07) | compose in runner | Terraform (small SKUs, scale-to-zero) | Terraform (HA SKUs, zones) |
| Identity | dev-issuer | dev-issuer | Entra (test tenant) + dev-issuer for demo personas | Entra |
| LLM | stub / dev AOAI | stub (recorded fixtures) | AOAI staging deployment (small quota) | AOAI prod deployment |
| Data | seeded synthetic | fixtures | synthetic demo tenants | demo/real |
| Purpose | inner loop | PR gate | pre-prod verification, evals vs live models, demos | the product |

Parity principle (restated from Phase 6): **code paths identical everywhere; only providers/SKUs differ, always behind ports with contract tests.**

## 2. Promotion pipeline (mechanics behind Phase 2 doc 08 §3)

```
merge to main
  → build+scan+sign images (tag: sha) → push ACR
  → terraform plan/apply (staging)                    [job: infra-staging]
  → migrate (staging)                                 [gated job, §4]
  → deploy staging (new ACA revisions, 100% on health)
  → verify-staging: smoke suite + contract tests + eval subset (live models)
  → [environment protection: manual approval — required reviewer]
  → terraform plan (prod) → apply if plan non-empty   [rare; usually no-op]
  → migrate (prod)                                    [gated job, §4]
  → deploy prod: new revision at 0% → health probes → traffic 100%
    (canary 10%→100% w/ auto-revert on 5xx/latency burn — enterprise flag)
  → post-deploy: synthetic golden-journey check (Playwright headless, stub-safe)
  → annotate: release marker → App Insights + dashboards + Sentry-style release tag
rollback: `just rollback prod` = traffic flip to previous revision (< 2 min)
  + migration posture per §4 (expand/contract makes schema a non-blocker)
```

Weekly **rollback drill** in staging (scripted: deploy, flip back, verify) — rollback is a rehearsed motion, not a document.

## 3. Configuration flow

Precedence (runtime): ACA env (from TF: topology facts — endpoints, identity client-ids) → Key Vault refs (secrets) → App Configuration (feature flags + tunables, live-refreshed via OpenFeature) → defaults in `Settings`. Rule: **a config value lives in exactly one tier** — endpoints never in App Config, flags never in env; the `Settings` schema documents each field's tier, and a CI check asserts no field is supplied by two tiers.

## 4. Migration gating (the risky job, made boring)

Migration job: separate pipeline step, migration DB role, `alembic upgrade head` wrapped with: pre-flight (pending revisions listed + linked to PRs; destructive-op linter blocks `DROP`/`ALTER … TYPE` outside contract-phase-labelled revisions), advisory lock (one migrator), post-flight (revision recorded to release annotation). Expand→migrate→contract (Phase 6 doc 03 §5) means the **previous app revision always runs against the new schema** — which is what makes the 0%→100% traffic flip and instant rollback safe. Contract-phase revisions ship in a later release with a `contract:` label and their own reviewer checklist.

## 5. Release cadence & versioning

Continuous to staging; prod promotion at will (portfolio) / weekly train (enterprise posture). Release notes generated from Conventional Commits (Phase 6 doc 01 §4); every release annotation carries: image SHAs, migration revisions, pack versions, prompt versions, model registry stages — **one release = one reproducible bill of materials** (the AP-2 mindset applied to deployment; this is also the answer to "what exactly is running in prod?" during an incident or audit).
