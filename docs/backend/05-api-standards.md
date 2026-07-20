# 05 — API Implementation Standards

Phase 2 doc 06 defined the conventions; this document is the implementation kit that makes them uniform.

## 1. Router conventions

- One router per module; path constants from a shared registry (no string-drift between routes and tests).
- Response models are explicit `taxos_contracts` types — never ORM models, never dicts (`response_model` on every route; ruff plugin flags missing ones).
- Status codes: 201 + `Location` on create; 202 + job resource for async work (batches, computations, evidence packs); 204 for pure transitions with no body.
- Route handlers ≤ ~15 lines (parse → guard → service → shape); anything longer is service logic in the wrong place.

## 2. Pagination (cursor) — shared implementation

```python
class Page(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None          # opaque: base64(sort_key values + id)
    # no total_count by default — COUNT(*) on partitioned tables is a footgun;
    # endpoints that need counts expose a separate /stats aggregate

async def paginate(q: Select, cursor: Cursor | None, limit: int = 50) -> Page[T]:
    # keyset WHERE (sort_col, id) > (cursor.vals) ORDER BY sort_col, id LIMIT limit+1
```

Every collection endpoint uses `paginate` — hand-rolled pagination is a review reject. Sort keys documented per endpoint; cursors are signed (HMAC) so clients can't forge offsets into unscoped data.

## 3. Idempotency keys (POST) — shared dependency

`Idempotency-Key` header → Redis `SETNX idem:{tenant}:{route}:{key}` storing response hash + body for 24h: replay returns the stored response with `Idempotency-Replayed: true`; same key + different request hash → 422 problem (`idempotency-key-reuse`). Applied via a router-level dependency on every mutating POST (registry-checked in a contract test: any POST without it fails CI).

## 4. Concurrency (ETag/If-Match)

`version_id` (doc 03 §3) → `ETag: W/"{version}"` on GET; mutating routes require `If-Match`, raise `ConflictError` (412 problem) on mismatch. Approvals additionally verify `content_hash` in-body (the ETag protects the resource shape; the hash binds the human's intent to reviewed content — both, deliberately).

## 5. OpenAPI pipeline

1. Route annotations + contracts generate OpenAPI 3.1 at build (`just openapi > artifacts/openapi.json` — the artifact of record, versioned per release).
2. **spectral** ruleset (`.spectral.yml`) encodes Phase 2 doc 06 §3: problem+json error schemas on every 4xx/5xx, pagination envelope on collections, no floats in money fields, operationId naming, deprecation-header documentation.
3. **schemathesis** fuzzes the running test instance from the artifact in CI (auth-injected, per-endpoint budgets).
4. `openapi-typescript` generates the frontend client types (Phase 7 consumes; drift = frontend build failure).
5. Swagger UI/ReDoc mounted in non-prod only; prod docs are APIM developer portal (enterprise) or the published artifact.

## 6. Auth & security defaults (implementation checklist per endpoint)

| Check | Mechanism |
|---|---|
| RBAC guard present | `require(Perm.X)` dependency — contract test walks the route table and fails on unguarded routes (allow-list for `/healthz`, `/ws` handshake) |
| Tenant scope | Session RLS (doc 03 §1) + explicit entity-scope ABAC in services where applicable |
| Input bounds | Pydantic constraints on every field (lengths, ranges, enums); list sizes capped |
| Upload safety | Content-type allow-list, size caps (middleware), AV scan hook before Blob write, never trust filenames (server-generated keys) |
| Output discipline | `response_model` filtering (no over-serialisation), `exclude_none`, no internal ids beyond contract |
| Rate limits | Middleware (global) + route-class overrides (uploads, agent-runs) |
| Audit | Mutations audit via UoW by construction; denials audited in the error handler |

## 7. Tool Gateway specifics

Same kit + three extras: `require_tool_grant(tool_name)` dependency (verifies the calling agent's registry grant + run budget — Phase 2 doc 06 §2); run-context header (`X-Taxos-Run`) propagated into audit actor refs (`agent:{name}:run:{id}`); responses are `taxos_contracts` tool-output types shared with the agent's ToolClient — one schema, both sides, no drift.

## 8. Public API (R4) deltas

Versioned separately (`/public/v1`), APIM subscription + OAuth client-credentials, per-product quotas, webhook delivery with HMAC signatures + retry/backoff + dead-letter visibility to the tenant admin UI. Internal contracts are never exposed directly — public schemas are curated projections (breaking-change control at the edge where we can't coordinate consumers).
