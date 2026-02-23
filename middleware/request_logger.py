from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import time


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.time()
        response = await call_next(request)
        duration = (time.time() - start) * 1000
        print(
            f"[Request] {request.method} {request.url.path} completed_in={duration:.2f}ms status={response.status_code}"
        )
        return response
