# Phase 8 — Cloud Deployment (Azure)

**Product:** Enterprise Agentic Tax Operating System (TaxOS)
**Status:** Complete — awaiting stakeholder review
**Inputs:** Phase 2 doc 08 (deployment & cloud architecture, ADR-008), Phase 6 (containers, compose parity), NFR-01/03/05/12/14
**Last updated:** 2026-07-20

Phase 2 fixed the *architecture* (what runs where, HA/DR posture, CI/CD shape). This phase makes it *executable*: the Terraform estate, network/identity topology, promotion mechanics, the Kubernetes packaging target, and day-2 operations. Where Phase 2 already decided something, this phase references it rather than restating.

## Azure service map (decided estate)

| Brief item | Position | Where decided |
|---|---|---|
| Azure Container Apps | ✅ Primary compute (5 apps) | ADR-008 |
| Azure App Service | ❌ Not used — ACA covers the need; documented trade-off | ADR-008 |
| Kubernetes (AKS) | 📦 Alternative packaging target, Helm charts maintained + CI-validated (competency demonstration + graduation path) | ADR-008; doc 04 |
| Azure PostgreSQL Flexible Server | ✅ Zone-redundant HA, PITR, private endpoint | ADR-002; Phase 2 doc 08 |
| Azure Blob Storage | ✅ RA-GRS, WORM containers | Phase 2 doc 04 §5 |
| Azure Cache for Redis | ✅ | ADR-011 |
| Azure Service Bus | ✅ Prod event bus | ADR-003 |
| Azure OpenAI | ✅ Private endpoint, UK/EU region | Phase 3 |
| Azure AI Search | 🔜 Enterprise-tier retrieval swap behind `Retriever` port; Terraform module written, not deployed at MVP | ADR-002/015 |
| Azure Key Vault | ✅ RBAC mode, private endpoint | Phase 2 doc 07 §4 |
| Azure App Configuration | ✅ Feature flags (OpenFeature) | Phase 2 doc 08 §6 |
| Azure Monitor / App Insights / Log Analytics | ✅ OTel backend | Phase 2 doc 09 |
| Azure Container Registry | ✅ Premium (geo-replication enterprise), image signing | Phase 2 doc 08 |
| GitHub Actions | ✅ CI/CD | **ADR-018 (this phase)** |
| Azure DevOps | ❌ Not used — decision + enterprise mapping in ADR-018 |
| Terraform | ✅ Sole IaC tool | doc 01 |
| Docker | ✅ Everywhere | Phase 6 |

## Document map

| # | Document | Covers |
|---|----------|--------|
| 01 | [Terraform Estate](01-terraform.md) | Repo layout, state management, module design, naming, policy guardrails |
| 02 | [Network & Identity](02-network-identity.md) | VNet topology, private endpoints & DNS, managed identities, federated credentials, zero stored secrets |
| 03 | [Environments & Promotion](03-environments-and-promotion.md) | Env matrix, config/secret flow, pipeline mechanics, migration gating, rollback drills |
| 04 | [Kubernetes Target](04-kubernetes-target.md) | Helm chart estate, AKS reference topology, parity guarantees |
| 05 | [Operations](05-operations.md) | SKU/cost table, runbook index, backup/DR procedures, teardown/rebuild |
| — | [ADR-018](../architecture/adr/ADR-018-github-actions.md) | GitHub Actions over Azure DevOps |
