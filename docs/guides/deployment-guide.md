# Installation & Deployment Guide

## 1. Local (evaluation / development)

**Prerequisites:** Docker Desktop (or engine + compose v2), `just`, git. ~6GB RAM free.

```bash
git clone <repo> && cd taxos
cp .env.example .env          # defaults work out of the box
just up                       # pulls, builds, migrates, seeds `demo` profile
just demo                     # replays flagship agent run (stub-LLM) → opens dashboard
```

- Personas: `amara@dev` (Head of Tax) · `daniel@dev` (Preparer) · `priya@dev` (Reviewer/Risk) · `marcus@dev` (CFO) · `sofia@dev` (Admin) · `alex@dev` (Auditor) — password per `.env.example`.
- Real LLM locally (optional): set `TAXOS_AOAI__*` vars; stub mode is the default and is watermarked in the UI.
- Reset: `just seed profile=demo` (data only) / `just down && just up` (everything).
- Troubleshooting: `just logs [service]`; port conflicts and first-run OCR model pulls are the two known snags — see comments in `docker-compose.yml`.

## 2. Azure (staging/production)

**Prerequisites:** Azure subscription (Owner on target), Entra tenant, GitHub repo with Actions, `az` CLI ≥ 2.60, Terraform ≥ 1.8.

```
1. Bootstrap (once):        cd infra/global && terraform init && terraform apply
                            # state storage, ACR, budget alerts, OIDC federation for GitHub envs
2. Entra app registrations: tools/setup-entra.sh   # frontend + services + API scopes; outputs → tfvars
3. Environment:             cd infra/envs/staging && terraform init && terraform apply
                            # full estate: VNet, private endpoints, Postgres, Redis, SB, KV, ACA, AOAI…
4. First deploy:            push to main → pipeline builds, migrates, deploys staging
                            # prod: approve the environment gate
5. Seed & verify:           just seed-remote env=staging profile=demo
                            just smoke env=staging          # golden-journey headless check
```

Details: [Terraform estate](../cloud/01-terraform.md) · [network/identity](../cloud/02-network-identity.md) · [promotion mechanics](../cloud/03-environments-and-promotion.md). Regional default `uksouth` (+ `ukwest` DR assets). Demo-cost posture and teardown (`just infra-down`, ≤30-min rebuild): [operations §1](../cloud/05-operations.md).

## 3. Kubernetes (alternative target)

Same images, Helm estate in `deploy/helm/` — CI-validated on kind every PR. AKS values overlay + reference topology: [Kubernetes target](../cloud/04-kubernetes-target.md). `helm install taxos deploy/helm/taxos -f values-aks.yaml` against a cluster with workload identity + External Secrets configured.

## 4. Configuration reference

All settings are typed in `Settings` ([source of truth](../backend/02-application-architecture.md#3-dependency-injection--settings)); tier rules (env vs Key Vault vs App Config) in [promotion doc §3](../cloud/03-environments-and-promotion.md). `TAXOS_ENV=prod` hard-asserts: Entra-only issuer, OpenAPI off, stub-LLM off, debug endpoints absent (config validation fails closed on violations).

## 5. Upgrade & rollback

Upgrades ride the pipeline (expand→migrate→contract keeps rollback schema-safe); rollback = revision traffic flip (`just rollback <env>`, < 2 min) — [mechanics](../cloud/03-environments-and-promotion.md#2-promotion-pipeline-mechanics-behind-phase-2-doc-08-3). Never `terraform apply` and app-deploy in one change window unless the plan is topology-only additive.
