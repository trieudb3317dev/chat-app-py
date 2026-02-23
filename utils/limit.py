# rate limiting utilities

from fastapi import HTTPException
from time import time
from fastapi import Request

# For dependency factory caching
_LIMITERS = {}


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = (
            {}
        )  # key: identifier (e.g. IP), value: list of request timestamps

    def is_allowed(self, identifier: str) -> bool:
        now = time()
        if identifier not in self.requests:
            self.requests[identifier] = []

        # Remove timestamps outside the current window
        self.requests[identifier] = [
            timestamp
            for timestamp in self.requests[identifier]
            if now - timestamp < self.window_seconds
        ]

        if len(self.requests[identifier]) < self.max_requests:
            self.requests[identifier].append(now)
            return True
        else:
            return False

    def enforce(self, identifier: str):
        if not self.is_allowed(identifier):
            raise HTTPException(
                status_code=429, detail="Too many requests. Please try again later."
            )


def _get_limiter(max_requests: int, window_seconds: int) -> RateLimiter:
    key = (max_requests, window_seconds)
    if key not in _LIMITERS:
        _LIMITERS[key] = RateLimiter(max_requests, window_seconds)
    return _LIMITERS[key]


def rate_limit(max_requests: int = 10, window_seconds: int = 60):
    """Return a FastAPI dependency function that enforces rate limits.

    Usage in a route decorator: dependencies=[Depends(rate_limit(5, 60))]
    The limiter is keyed by (max_requests, window_seconds). The per-request
    identifier used is client IP plus request path, so limits are applied per
    IP per endpoint.
    """

    limiter = _get_limiter(max_requests, window_seconds)

    async def _dependency(request: Request):
        # prefer X-Forwarded-For if behind proxy
        forwarded = request.headers.get("x-forwarded-for")
        client = (forwarded.split(",")[0].strip() if forwarded else None) or (
            request.client.host if request.client else "unknown"
        )

        identifier = f"{client}:{request.url.path}"
        limiter.enforce(identifier)

    return _dependency
