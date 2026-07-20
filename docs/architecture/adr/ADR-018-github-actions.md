# ADR-018 — GitHub Actions for CI/CD (Azure DevOps mapped, not adopted)

**Status:** Accepted · 2026-07-20 · Principles: AP-5 · Context: Phase 8; brief lists both GitHub Actions and Azure DevOps

## Context
One CI/CD system must own the pipeline (Phase 2 doc 08 §3, Phase 8 doc 03). The repository lives on GitHub (portfolio requirement, Phase 12); the deployment target is Azure (where Azure DevOps has incumbency in enterprise settings, though Microsoft's own investment has visibly consolidated on GitHub since acquiring it).

## Decision
**GitHub Actions** for all pipelines: PR checks, main promotion, nightly, drift detection, DR rehearsal. Azure access via **OIDC federated credentials** per environment (no stored secrets); environment protection rules provide the prod approval gate; reusable workflows + composite actions keep pipeline code DRY and reviewable in the same PRs as the code they build.

## Alternatives
1. **Azure DevOps Pipelines** — genuinely strong (environments, approvals, service connections), and still the incumbent in many Big Four estates. Rejected because: the repo, reviews, issues, and portfolio surface are on GitHub — splitting SCM from CI adds integration seams (status checks, PR gating) with zero capability gain; GitHub environments + OIDC now cover the historical ADO advantages (approvals, secretless cloud auth); and Microsoft's roadmap gravity (GitHub Advanced Security, Copilot, Actions investment) points one direction. **Enterprise mapping documented for interviews:** every concept transfers 1:1 (workflow↔pipeline YAML, environment protection↔ADO environments+approvals, OIDC federation↔workload identity service connections, reusable workflows↔templates) — adopting ADO in a client estate is a syntax exercise, not a re-learning.
2. **Both (Actions CI + ADO CD)** — the worst option: two systems, two RBAC models, two audit surfaces, split provenance for the release bill of materials (Phase 8 doc 03 §5).
3. **Jenkins/self-hosted** — operational liability with no benefit at this scale; rejected without ceremony.

## Consequences
- (+) One provenance chain: commit → checks → images → deploy annotations, all in one audit surface; secretless cloud auth; pipeline changes reviewed with code changes.
- (+) Free tier covers the portfolio comfortably; runners scale without ops.
- (−) Enterprise buyers on ADO see "not our stack" → answered by the documented mapping + the fact that all pipeline logic lives in `just` targets (Phase 6 doc 01 §3), so the CI file is a thin shell over portable commands — the real migration cost is near zero and stated as such.
- (−) GitHub-hosted runner limits (network egress to private endpoints) → deploy steps use `azure/login` OIDC + public control-plane APIs only (ACA/ACR/TF state via service endpoints); no runner ever needs VNet access. If that changes: self-hosted runner in the VNet is a one-module addition (documented in `infra/modules/`, not built).
