# logx/middleware.py
import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .context import clear_span, set_request_context
from .structured import log_span


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        corr = request.headers.get("x-correlation-id")
        set_request_context(correlation_id=corr)
        t0 = time.monotonic_ns()
        log_span(
            "operation_started",
            "http_request",
            {"path": request.url.path, "method": request.method},
            logging.INFO,
        )
        try:
            resp: Response = await call_next(request)
            dur_ms = (time.monotonic_ns() - t0) // 1_000_000
            log_span(
                "operation_completed",
                "http_request",
                {
                    "path": request.url.path,
                    "method": request.method,
                    "status": resp.status_code,
                    "duration_ms": int(dur_ms),
                },
                logging.INFO,
            )
            return resp
        except Exception as e:
            dur_ms = (time.monotonic_ns() - t0) // 1_000_000
            log_span(
                "operation_failed",
                "http_request",
                {
                    "path": request.url.path,
                    "method": request.method,
                    "duration_ms": int(dur_ms),
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                logging.ERROR,
            )
            raise
        finally:
            clear_span()
