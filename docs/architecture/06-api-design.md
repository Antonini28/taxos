# 06 — API Design

## 1. Gateway topology

| Stage | Gateway | Responsibilities |
|---|---|---|
| MVP | Azure Container Apps ingress + FastAPI middleware stack | TLS, routing, CORS, security headers, request-size caps, rate limiting (Redis token bucket), request-ID injection |
| Enterprise (R3) | **Azure API Management** in front | + WAF policies, subscription keys for the public API (FR-706), per-product quotas, developer portal, response caching at edge |

The middleware stack is written once and stays valid under APIM — APIM adds policy, it doesn't replace app-level enforcement (defence in depth: the app never assumes a well-behaved edge).

## 2. API surfaces (three, deliberately separate)

| Surface | Path root | Consumer | Auth |
|---|---|---|---|
| **Web API** | `/api/v1/*` | Next.js frontend | User JWT (OIDC) |
| **Tool Gateway** | `/tool-gateway/v1/*` | taxos-agents only | Service identity (client-credentials) + per-agent grant claims + run context header |
| **Public API** (R4) | `/public/v1/*` | Client integrations | APIM subscription + OAuth client credentials |

Separating the Tool Gateway from the Web API is a governance decision, not a convenience: the agent-callable surface is small, explicitly enumerated, versioned independently, and **has no approval, user-management, or filing endpoints by construction** (ADR-012). A prompt-injected agent cannot call what does not exist on its surface.

## 3. REST conventions (enforced by review checklist + spectral lint on the OpenAPI doc)

- **Resources, plural nouns, kebab-case:** `/api/v1/work-items/{id}/transitions`, `/api/v1/batches/{id}/validation-report`.
- **Versioning:** URI major version (`/v1/`); additive changes are non-breaking; breaking changes ⇒ `/v2/` with ≥1 minor-release deprecation overlap and `Deprecation`/`Sunset` headers. URI versioning chosen over header versioning for debuggability and cache-key simplicity — the pragmatic enterprise trade-off.
- **Errors:** RFC 9457 `application/problem+json` everywhere: `{type, title, status, detail, instance, trace_id, errors[]}` — `trace_id` links straight to the distributed trace (doc 09).
- **Pagination:** cursor-based (`?cursor=&limit=`) on all collections (offset pagination degrades on partitioned transaction tables); stable sort keys documented per endpoint.
- **Filtering:** whitelisted query params only; no generic query-language pass-through (injection surface).
- **Idempotency:** all POSTs that create business state accept `Idempotency-Key`; server stores key→response for 24h (retries are safe by contract, which the outbox/queue world requires anyway).
- **Concurrency:** optimistic — mutable resources carry `ETag`; writes require `If-Match`; 412 on staleness. Approvals additionally bind to `content_hash` in the body (US-402).
- **Money:** integer minor units + ISO-4217 currency code in payloads (`{"amount_minor": 1250000, "currency": "GBP"}`); serialising floats for money fails contract tests.
- **Time:** RFC 3339 UTC everywhere; tax-period semantics carried as explicit `{period_key, period_start, period_end}` objects, never inferred from timestamps.

## 4. Contract-first workflow

1. Pydantic models + FastAPI routers generate the OpenAPI 3.1 document — the artifact of record, published per build.
2. `spectral` lints the spec in CI (naming, error-shape, pagination rules above codified as custom rules).
3. `schemathesis` runs property-based contract tests against a live test instance in CI (fuzzes every documented endpoint for contract violations).
4. Frontend types are generated from the spec (`openapi-typescript`) — drift between backend and frontend is a build failure, not a runtime bug.
5. Swagger UI + ReDoc served in non-prod; the public developer portal (R4) is APIM's.

## 5. Rate limiting & quotas

| Scope | Limit (MVP defaults) | Mechanism |
|---|---|---|
| Per user | 60 req/min sustained, burst 120 | Redis token bucket, key `rl:u:{user}` |
| Per tenant | 600 req/min | `rl:t:{tenant}` — protects noisy-neighbour in multi-tenant mode |
| Tool Gateway per run | 200 calls/run, 30/min | Run-scoped bucket — a looping agent throttles itself, not the platform |
| Uploads | 10 concurrent batches/tenant; 500MB/file | Ingestion fairness (doc 05 §6) |
| Public API (R4) | Per APIM product/subscription | APIM policy |

429 responses carry `Retry-After`; limits are feature-flag tunable per tenant (enterprise tiering hook).

## 6. GraphQL position (ADR-010)

Not adopted at MVP. The honest trade-off: GraphQL's benefit (client-shaped aggregation across many resources) is real for the dashboard tier, but its costs — authZ-per-field complexity on top of RBAC+ABAC+RLS, query-cost control, cache fragmentation, a second contract toolchain — are exactly the places where a governance-heavy platform can't afford subtle bugs. The dashboard need is met with purpose-built read endpoints (`/api/v1/dashboards/executive`) backed by the `rpt_*` aggregates. Revisit trigger (recorded in ADR-010): if ≥3 distinct client applications demand differently-shaped reads of the same domains, introduce GraphQL as a **read-only BFF** over the service interfaces — never for mutations.

## 7. Representative endpoint map (MVP web API)

```
POST   /api/v1/batches                          # upload (multipart) → 202 + batch resource
GET    /api/v1/batches/{id}/validation-report
GET    /api/v1/entities/{id}/obligations?period=
POST   /api/v1/obligations/{id}/computations    # trigger deterministic run → 202
GET    /api/v1/computations/{id}                # result + box values
GET    /api/v1/computations/{id}/lines/{line}/lineage   # US-202 drill-down
POST   /api/v1/work-items/{id}/transitions      # workflow moves (guarded)
POST   /api/v1/work-items/{id}/approvals        # If-Match + content_hash + SoD checks
GET    /api/v1/anomalies?status=OPEN&severity=
POST   /api/v1/anomalies/{id}/disposition
POST   /api/v1/agent-runs                       # instruct the agent team (US-401)
GET    /api/v1/agent-runs/{id}                  # plan, steps, status (also via WS)
GET    /api/v1/dashboards/executive
POST   /api/v1/work-items/{id}/evidence-pack    # → 202, Blob URL on completion
GET    /api/v1/audit-events?subject=&actor=     # auditor read surface
```
