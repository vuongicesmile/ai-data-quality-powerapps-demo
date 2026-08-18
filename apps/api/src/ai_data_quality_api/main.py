"""FastAPI application factory and connector-ready OpenAPI surface."""

from data_quality.domain.errors import PlatformError
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .router import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Data Quality Platform API",
        version="1.0.0",
        description="Provider-neutral Generic Dataset workflow for Power Apps",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:4173", "http://127.0.0.1:4173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(PlatformError)
    async def platform_error_handler(_request: Request, exc: PlatformError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"type": exc.__class__.__name__, "message": str(exc)}},
        )

    @app.get("/health", include_in_schema=False)
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(router)
    return app


app = create_app()
