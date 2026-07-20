"""
Structured-ish logging setup + a request-logging middleware.

Kept as plain stdlib logging with a consistent format rather than pulling
in structlog/loguru here — easy to swap later once you wire this into
Prometheus/Grafana/Loki (per your infra plan), but stdlib logging is
enough to get every request's method/path/status/duration on one line
right now.
"""
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


def configure_logging(debug: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs one line per request and attaches X-Request-ID for tracing."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        logger = logging.getLogger("bytesentinel.request")

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        response.headers["X-Request-ID"] = request_id
        logger.info(
            "%s %s -> %s (%.1fms) [request_id=%s]",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        return response
