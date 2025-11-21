# logx/middleware.py

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .context import clear_span, set_request_context


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        corr = request.headers.get("x-correlation-id")
        set_request_context(correlation_id=corr)
        try:
            resp: Response = await call_next(request)
            return resp
        finally:
            clear_span()
