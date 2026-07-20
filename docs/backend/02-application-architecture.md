# 02 — Application Architecture (taxos-api)

## 1. App composition (apps/api/main.py — assembly only)

```python
def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(
        title="TaxOS API", version=settings.release,
        openapi_url="/api/v1/openapi.json" if settings.expose_openapi else None,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,                      # engine/redis/otel startup-shutdown
    )
    # middleware: outermost → innermost
    app.add_middleware(RequestIDMiddleware)      # X-Request-ID in, generate if absent
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)      # Redis token bucket (doc 06 §5, Phase 2)
    app.add_middleware(BodySizeLimitMiddleware)
    app.add_middleware(OTelMiddleware)           # spans + trace_id into request state
    register_error_handlers(app)                 # → problem+json (§4)
    for module in MODULES:                       # each module exports `router` + `tool_router`
        app.include_router(module.router, prefix="/api/v1")
    app.include_router(tool_gateway_router, prefix="/tool-gateway/v1")
    app.include_router(ws_router)                # /ws
    return app
```

## 2. Module template (every domain module looks like this)

```
taxos_core/<module>/
├── __init__.py        # exports: service interface, events — the ONLY public surface
├── router.py          # FastAPI routes: parse → authz → call service → shape response. NO logic.
├── service.py         # use-cases; orchestrates repositories inside UoW; raises domain errors
├── models.py          # SQLAlchemy models (module-private)
├── repository.py      # query layer over models (module-private)
├── events.py          # this module's domain event types (re-exported from taxos_contracts)
├── policies.py        # ABAC policy functions for this module's actions (pure, tested)
└── internal/          # anything else (engine hosts, mappers, validators)
```

The router/service/repository split is not ceremony: **routers are untestable-logic quarantine** (they contain only translation), **services are where transactions live** (one service method = one UoW = one atomic business action), repositories keep SQLAlchemy specifics out of use-case code (and are what RLS session fixtures exercise in tests).

## 3. Dependency injection & settings

- **DI via FastAPI dependencies only** — no container framework. Composition roots (`apps/*`) build singletons (engine, redis, publishers); request-scoped objects (session/UoW, `AuthzContext`) are dependencies. Services take explicit constructor args → trivially unit-testable.
- **Settings:** `pydantic-settings`, one `Settings` tree per app, sourced env-first (12-factor; Key Vault/App Config populate env in Azure — doc 08). Every field typed + documented; `Settings()` is constructed once in the composition root and injected — `os.environ` access anywhere else is lint-banned. Secrets fields use `SecretStr` (keeps them out of reprs/logs).

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TAXOS_", env_nested_delimiter="__")
    env: Literal["local", "ci", "staging", "prod"]
    release: str = "dev"
    database: DatabaseSettings          # dsn: SecretStr, pool sizes, statement timeout
    redis: RedisSettings
    auth: AuthSettings                  # issuer, audience, jwks_url, session TTLs
    features: FeatureFlagSettings       # OpenFeature provider config
    expose_openapi: bool = True         # False in prod (APIM serves docs)
```

## 4. Error handling — one taxonomy, one shape

Domain code raises typed exceptions; **only** the boundary translates them (RFC 9457, Phase 2 doc 06 §3):

```python
class DomainError(Exception):
    status = 500; type_suffix = "internal"; title = "Internal error"

class NotFoundError(DomainError):        status = 404; type_suffix = "not-found"
class PermissionDeniedError(DomainError):status = 403; type_suffix = "forbidden"
class ConflictError(DomainError):        status = 409; type_suffix = "conflict"      # ETag/state
class ValidationFailed(DomainError):     status = 422; type_suffix = "validation"    # carries errors[]
class SoDViolation(PermissionDeniedError): type_suffix = "segregation-of-duties"
class StaleApprovalError(ConflictError):   type_suffix = "stale-approval"            # content_hash mismatch

@app.exception_handler(DomainError)
async def domain_error_handler(request, exc):
    problem = Problem(
        type=f"https://taxos.dev/problems/{exc.type_suffix}",
        title=exc.title, status=exc.status, detail=str(exc),
        instance=request.url.path, trace_id=current_trace_id(),
        errors=getattr(exc, "errors", None),
    )
    if exc.status == 403:                       # every denial is audited (Phase 2 doc 07)
        await audit_denied_attempt(request, exc)
    return ORJSONResponse(problem.model_dump(exclude_none=True), status_code=exc.status)
```

Rules: services never import HTTP concepts; handlers never contain logic; unexpected exceptions → generic 500 problem (no internals leak) + ERROR log with trace_id; 4xx are logged INFO (they're user behaviour, not incidents — alert-fatigue discipline from doc 09).

## 5. AuthN/AuthZ dependencies (implementation of Phase 2 doc 07 §2)

```python
async def current_principal(request: Request, settings: AuthDep) -> Principal:
    token = extract_session(request)                 # httpOnly cookie (BFF) or Bearer (service)
    claims = await validate_jwt(token, settings)     # signature, exp, aud, iss; jwks cached
    return Principal(sub=claims.sub, tenant_id=claims.tenant_id,
                     kind=claims.kind, session_id=claims.session_id)

async def authz(request, principal=Depends(current_principal)) -> AuthzContext:
    ctx = await load_authz_context(principal)        # roles + entity scopes; Redis cache-aside
    request.state.authz = ctx
    return ctx

def require(permission: Permission):                 # route-level RBAC guard
    async def guard(ctx: AuthzContext = Depends(authz)) -> AuthzContext:
        if not ctx.has(permission): raise PermissionDeniedError(permission)
        return ctx
    return guard

# usage — the pattern for EVERY route:
@router.post("/work-items/{wid}/approvals")
async def grant_approval(wid: UUID, body: ApprovalRequest,
                         ctx: AuthzContext = Depends(require(Perm.APPROVAL_GRANT)),
                         svc: ApprovalService = Depends(approval_service)):
    return await svc.grant(wid, body, ctx)           # ABAC (SoD, scope, state) inside the service
```

RBAC at the route (cheap, declarative, enumerable — the security review reads the route table); ABAC inside the service where the facts live (SoD needs the work item loaded). The Tool Gateway uses the same machinery with `Principal(kind="agent")` + per-agent grant verification in its `require_tool_grant` dependency.

## 6. WebSocket endpoint

`/ws` authenticates the session cookie on connect, registers (tenant, entity-scopes) server-side, subscribes to Redis pub/sub bridge channels, and filters every outbound frame against the connection's scope before send (Phase 2 doc 05 §5). Heartbeat ping/pong 30s; token-expiry closes with policy code; client reconnect + React Query fallback is Phase 7's concern.
