# ADR-008 — Azure Container Apps for compute (AKS as the graduation path)

**Status:** Accepted · 2026-07-20 · Principles: AP-5

## Context
Compute options on Azure for containerised services: AKS (full Kubernetes), Container Apps (managed K8s abstraction with KEDA/Dapr built in), App Service (webapp PaaS), Functions (FaaS). Drivers: small team, KEDA-style queue autoscaling, scale-to-zero for bursty agent/worker loads, VNet integration, revision-based deploys, cost control for a portfolio deployment.

## Decision
**Azure Container Apps** for all five deployables (frontend, api, agents, workers, scheduler) in a VNet-injected environment. Terraform-managed; revisions used for blue/green-style traffic shifting; KEDA scalers on HTTP concurrency (api) and queue/bus depth (workers/agents); scale-to-zero on agents and staging.

## Alternatives considered
1. **AKS** — maximal control and the "enterprise default" optics, but: cluster upgrades, node pools, ingress controllers, cert management, RBAC-on-K8s — a part-time platform-engineering job that adds zero product value at this scale, plus always-on node cost. **Graduation triggers documented:** need for service mesh, custom CRDs/operators, GPU pools, or org-mandated K8s estate. Because everything ships as OCI images with externalised config, the move is repackaging (Helm charts), not redesign — and Phase 8 documents the K8s manifests as an alternative deployment target to demonstrate the competency.
2. **App Service** — fine for api/frontend but weak KEDA-equivalent story for queue-driven workers and no scale-to-zero economics for the agent runtime.
3. **Azure Functions for workers** — duration limits and bindings-lock-in vs Celery's routing/retry semantics we already need; mixing paradigms raises cognitive cost.

## Consequences
- (+) Zero cluster ops; autoscaling semantics we need are first-class; consumption pricing keeps idle cost near zero (doc 08 §7).
- (+) Revisions give instant rollback + canary without extra tooling.
- (−) Less control (no daemonsets, limited pod-level knobs); some enterprise reviewers read "not AKS" as junior → countered explicitly in docs: the ADR shows the trade-off was priced, and the K8s path is prepared, which is the more senior signal.
- (−) Container Apps consumption cold starts on scale-from-zero (~seconds) → agents/workers are async consumers where seconds are invisible; api keeps min-replicas ≥ 2.
