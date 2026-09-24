from urllib.parse import urlencode

import structlog
from fastapi import FastAPI, Request
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings

logger = structlog.get_logger(__name__)


class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _is_quickbooks_callback(request: Request) -> bool:
    prefix = get_settings().api_v1_prefix.rstrip("/")
    return request.url.path == f"{prefix}/finance/quickbooks/oauth/callback"


def quickbooks_oauth_redirect(outcome: str) -> RedirectResponse:
    target = get_settings().quickbooks_frontend_return_url
    separator = "&" if "?" in target else "?"
    return RedirectResponse(
        f"{target}{separator}{urlencode({'quickbooks': outcome})}",
        status_code=303,
        headers={
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
            "Referrer-Policy": "no-referrer",
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException):
        if _is_quickbooks_callback(request):
            return quickbooks_oauth_redirect("failed")
        return await http_exception_handler(request, exc)

    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(request: Request, exc: RequestValidationError):
        if _is_quickbooks_callback(request):
            return quickbooks_oauth_redirect("failed")
        return await request_validation_exception_handler(request, exc)

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        if _is_quickbooks_callback(request):
            return quickbooks_oauth_redirect("failed")
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"message": exc.message}},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        if _is_quickbooks_callback(request):
            logger.exception(
                "quickbooks_oauth_callback_unhandled_error",
                path=request.url.path,
                request_id=getattr(request.state, "request_id", None),
                error_type=type(exc).__name__,
            )
            return quickbooks_oauth_redirect("failed")
        logger.exception(
            "unhandled_error",
            path=request.url.path,
            request_id=getattr(request.state, "request_id", None),
            error=str(exc),
        )
        return JSONResponse(
            status_code=500,
            content={"error": {"message": "Internal server error"}},
        )
