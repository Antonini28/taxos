# 04 — Kubernetes Packaging Target

ADR-008 chose Container Apps and committed to keeping the Kubernetes path *prepared* — both as the graduation route (org-mandated K8s estates are the Big Four norm) and as a competency demonstration. This document keeps that commitment concrete and cheap.

## 1. Helm chart estate (`deploy/helm/`, maintained in-repo)

```
deploy/helm/taxos/
├── Chart.yaml                     # umbrella chart
├── values.yaml                    # defaults; values-aks.yaml overlay
├── charts/
│   ├── api/  frontend/  agents/  workers/  scheduler/
│   │   └── templates/: deployment, service, hpa/keda-scaledobject,
│   │       pdb, networkpolicy, serviceaccount (workload identity)
└── templates/: shared configmaps, external-secrets bindings, ingress
```

Design mappings (1:1 with the ACA deployment — same images, same env contract):

| Concern | ACA | AKS equivalent in charts |
|---|---|---|
| Autoscale | KEDA scalers (built-in) | KEDA `ScaledObject` (same triggers: HTTP concurrency, Service Bus depth, Redis queue length) |
| Identity | Managed identity | **Workload Identity** (federated SA → same MIs — doc 02 grants unchanged) |
| Secrets | KV references | External Secrets Operator → same Key Vault |
| Ingress | ACA ingress | NGINX ingress + cert-manager (or AGIC enterprise) |
| Revisions/rollback | ACA revisions | Deployment rollout history + `helm rollback` |
| Scheduler singleton | single-replica app | Deployment replicas:1 + PDB + leader-election lock (already in app — Phase 2 doc 05 §4 — so K8s adds nothing to get right) |
| Isolation (ADR-012) | separate apps + identities | Namespaces `taxos-core` / `taxos-agents` + NetworkPolicies (agents → api :https only; agents ↛ postgres) |

## 2. AKS reference topology (documented, not deployed at MVP)

Private AKS (uksouth, 2 zones) · system pool (2×B4ms) + user pool (autoscaling) · Azure CNI overlay · workload identity enabled · same VNet/private-endpoint estate as doc 02 (the data plane doesn't change at all — only compute swaps) · Terraform module `modules/aks/` written alongside the ACA modules, gated by variable.

## 3. Parity guarantee (what keeps this real, not shelf-ware)

CI job `helm-validate` on every PR touching apps or charts: `helm template` + `kubeconform` schema validation + `helm test` dry-run against a **kind** cluster with the compose-equivalent stack (Postgres/Redis in-cluster, Azurite) — booting the full platform to health checks. This is ~4 minutes of CI and means the K8s story is *demonstrably working*, not aspirational: the portfolio claim is "same artifacts deploy to compose, Container Apps, and Kubernetes, and CI proves the third continuously."

## 4. When graduation actually happens (restating ADR-008 triggers with the runway now visible)

Service mesh requirement · custom operators/CRDs · GPU node pools (autoencoder era, ADR-017) · org-mandated AKS estate. Effort estimate with this chart estate in place: days (values + ingress + DNS), not a migration project — which was the entire point of paying the small continuous parity cost.
