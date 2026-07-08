from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Phase 1 API scaffold for Iron House OS.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name}

    @app.get("/readiness", tags=["system"])
    def readiness() -> dict[str, object]:
        return {
            "status": "ready",
            "service": settings.app_name,
            "api_prefix": settings.api_v1_prefix,
            "checks": {
                "api_router": "mounted",
                "cors": "configured",
                "docs": "enabled",
                "takeoff_engine": "enabled",
                "estimate_handoff": "enabled",
                "project_readiness": "enabled",
            },
        }

    return app


app = create_app()
