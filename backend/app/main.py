from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.services.document_audit import configure_document_audit_store
from app.services.document_audit_store import create_document_audit_store_from_environment
from app.services.system_readiness import get_system_readiness


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    configure_document_audit_store(create_document_audit_store_from_environment())

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Iron House OS API.",
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
    def readiness(response: Response) -> dict[str, object]:
        report = get_system_readiness(probe_runtime=True)
        if report["status"] != "ready":
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return report

    return app


app = create_app()
