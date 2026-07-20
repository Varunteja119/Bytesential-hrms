"""
Global exception handling.

Why: without this, an unhandled exception anywhere in a route returns
FastAPI's default 500 with a raw traceback in debug mode (a stack-trace
leak in prod) or an opaque "Internal Server Error" with no structure.
This gives every error — expected or not — the same JSON shape, and logs
unexpected ones with a request-scoped identifier for tracing.
"""
import logging
import uuid

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger("bytesentinel")


class AppError(Exception):
    """Base class for domain/business-logic errors raised anywhere in app/services."""

    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _error_response(status_code: int, message: str, request_id: str | None = None) -> JSONResponse:
    body = {"error": {"message": message}}
    if request_id:
        body["error"]["request_id"] = request_id
    return JSONResponse(status_code=status_code, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return _error_response(exc.status_code, exc.message)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        # Preserve FastAPI's own headers (e.g. WWW-Authenticate on 401s)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"message": exc.detail}},
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": {"message": "Validation failed", "details": exc.errors()}},
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        # e.g. duplicate unique key that slipped past an app-level check
        logger.warning("DB integrity error: %s", exc)
        return _error_response(status.HTTP_409_CONFLICT, "Resource conflict (likely a duplicate)")

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = str(uuid.uuid4())
        logger.exception("Unhandled exception [request_id=%s]", request_id)
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Internal server error",
            request_id=request_id,
        )
