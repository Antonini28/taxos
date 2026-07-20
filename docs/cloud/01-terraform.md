# 01 — Terraform Estate

## 1. Layout (in-repo `infra/`)

```
infra/
├── modules/                        # reusable, versioned by repo tag
│   ├── network/                    # vnet, subnets, NSGs, private DNS zones
│   ├── postgres/                   # flexible server, HA, roles, RLS-force bootstrap
│   ├── redis/  ├── servicebus/  ├── storage/       # incl. WORM policies
│   ├── keyvault/  ├── appconfig/  ├── acr/
│   ├── observability/              # log analytics, app insights, dashboards-as-code, alerts
│   ├── aca-env/                    # container apps environment (VNet-injected)
│   ├── aca-app/                    # one container app (revision config, KEDA scalers, probes, identity)
│   ├── openai/                     # AOAI account + deployments (model version pinned)
│   └── aisearch/                   # written, gated off by variable (enterprise tier)
├── envs/
│   ├── staging/   # main.tf composing modules + staging.tfvars
│   └── prod/      # same composition, prod.tfvars (SKUs, replica counts, zones)
├── global/                         # once-per-subscription: state storage, ACR, DNS zones, budget alerts
└── policies/                       # Azure Policy assignments (see §4)
```

Rules: **environments differ by tfvars, never by resource composition** (drift between staging and prod topology is a bug class we design out); modules pin provider versions; no module ever creates identities *and* grants them broad roles in one place (separation reviewed).

## 2. State & execution

- Remote state: Azure Storage backend (`global/` bootstraps it), one state file per env root + `global`; state storage is versioned, private-endpoint-only, with resource locks.
- Execution: **CI-only applies** (GitHub Actions with OIDC federation — no human runs `apply` against prod from a laptop; `plan` output posts to the PR, apply happens on merge with environment protection). Local `plan` against staging permitted for development (read-only credentials).
- Drift detection: nightly `terraform plan -detailed-exitcode` per env → non-empty plan raises a ticket (console changes are found within 24h, and the answer is "put it in code", not "click it back").

## 3. Module design standards

- Every module: `README.md` (inputs/outputs/example), typed variables with validation blocks, sensible `prod`/`nonprod` SKU presets, diagnostic settings wired to Log Analytics by default (observability is not opt-in), tags enforced (`env`, `system=taxos`, `owner`, `cost-centre`).
- Naming: CAF-aligned convention `taxos-<env>-<service>[-n]` via a shared locals module — greppable, sortable, no snowflakes.
- Outputs expose IDs + private endpoint FQDNs only — never keys/connection strings (identity-based access everywhere, doc 02; the few unavoidable secrets are written by the module directly into Key Vault, never through TF outputs/state where avoidable, and state access is treated as privileged regardless).

## 4. Policy guardrails (Azure Policy, assigned at RG scope)

Deny: public network access on data services · storage accounts without infrastructure encryption · resources outside `uksouth`/`ukwest` (NFR-03 residency) · Container Apps without system-assigned identity. Audit: missing tags, missing diagnostic settings, Key Vault without purge protection. These make review guarantees survive human error — the same defence-in-depth philosophy as RLS under the app.

## 5. What Terraform does *not* manage

App deployments (revisions are pushed by the CD pipeline via `az containerapp update` — image tags change too often for TF state), Alembic migrations (pipeline job, doc 03 §4), AOAI model *content* configuration beyond deployments, MLflow-registered models, rule packs. Boundary rule: **Terraform owns topology; pipelines own artifacts.** Both are code; they version at different speeds.
