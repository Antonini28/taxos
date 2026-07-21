"""taxos-api entrypoint — app assembly only (Phase 6 doc 02 §1).

US-101 scope: factory, request-ID + security-headers middleware, problem+json
error boundary, health endpoints. Domain routers mount here as modules land.
"""

import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from taxos_core.shared.config import Settings

from taxos_contracts import Problem


class DomainError(Exception):
    """Base of the typed error taxonomy (Phase 6 doc 02 §4)."""

    status = 500
    type_suffix = "internal"
    title = "Internal error"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(
        title="TaxOS API",
        version=settings.release,
        openapi_url="/api/v1/openapi.json" if settings.expose_openapi else None,
    )
    app.state.settings = settings

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        problem = Problem(
            type=f"https://taxos.dev/problems/{exc.type_suffix}",
            title=exc.title,
            status=exc.status,
            detail=str(exc) or None,
            instance=request.url.path,
            trace_id=getattr(request.state, "request_id", None),
        )
        return JSONResponse(
            problem.model_dump(exclude_none=True),
            status_code=exc.status,
            media_type="application/problem+json",
        )

    @app.get("/healthz", tags=["platform"])
    async def healthz() -> dict[str, str]:
        """Liveness — process is up."""
        return {"status": "ok", "release": settings.release}

    @app.get("/readyz", tags=["platform"])
    async def readyz() -> dict[str, str]:
        """Readiness — dependencies reachable (DB/Redis checks land with persistence layer)."""
        return {"status": "ok", "env": settings.env}

    return app


app = create_app()
