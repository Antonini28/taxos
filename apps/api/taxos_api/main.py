"""taxos-api entrypoint — app assembly only (Phase 6 doc 02 §1).

Domain routers mount here; no business logic lives in this file, ever.
"""

import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from taxos_contracts.problem import FieldError
from taxos_core.shared.config import Settings

from taxos_api.errors import DomainError
from taxos_api.routers import agent_runs, batches, computations, dashboards, work_items
from taxos_contracts import Problem
from taxos_core import models_registry  # noqa: F401 — completes Base.metadata (see its docstring)


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

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """FastAPI's own validation errors must speak problem+json too — one error shape
        across the whole API, or clients need two parsers (Phase 2 doc 06 §3)."""
        problem = Problem(
            type="https://taxos.dev/problems/validation",
            title="Validation failed",
            status=422,
            detail="Request failed schema validation",
            instance=request.url.path,
            trace_id=getattr(request.state, "request_id", None),
            errors=[
                FieldError(field=".".join(str(p) for p in e["loc"]), message=e["msg"])
                for e in exc.errors()
            ],
        )
        return JSONResponse(
            problem.model_dump(exclude_none=True),
            status_code=422,
            media_type="application/problem+json",
        )

    app.include_router(batches.router, prefix="/api/v1")
    app.include_router(computations.router, prefix="/api/v1")
    app.include_router(work_items.router, prefix="/api/v1")
    app.include_router(agent_runs.router, prefix="/api/v1")
    app.include_router(dashboards.router, prefix="/api/v1")

    @app.get("/healthz", tags=["platform"])
    async def healthz() -> dict[str, str]:
        """Liveness — process is up."""
        return {"status": "ok", "release": settings.release}

    @app.get("/readyz", tags=["platform"])
    async def readyz() -> dict[str, str]:
        """Readiness — dependencies reachable (DB/Redis probes land with the worker tier)."""
        return {"status": "ok", "env": settings.env}

    return app


app = create_app()
