"""Idempotency middleware for POST/PATCH requests.

Implements RFC 9413 idempotency pattern:
- Requires Idempotency-Key header on state-changing requests
- Stores response in Redis with 24h TTL
- Deduplicates identical requests by key
"""

from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger(__name__)


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce and validate idempotency keys on POST/PATCH.

    Note: Full Redis integration comes in next sprint.
    This is a placeholder for the idempotency validation framework.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        """Validate idempotency key requirement on state-changing requests.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response or 422 if idempotency key missing/invalid
        """
        if request.method in ("POST", "PATCH", "PUT", "DELETE"):
            idempotency_key = request.headers.get("idempotency-key")

            if not idempotency_key:
                logger.warning(
                    "missing_idempotency_key",
                    method=request.method,
                    path=request.url.path,
                )
                return Response(
                    content='{"error_code":"MISSING_IDEMPOTENCY_KEY","message":"Idempotency-Key header required"}',
                    status_code=422,
                    media_type="application/json",
                )

            if len(idempotency_key) > 255:
                logger.warning(
                    "invalid_idempotency_key",
                    length=len(idempotency_key),
                )
                return Response(
                    content='{"error_code":"INVALID_IDEMPOTENCY_KEY","message":"Idempotency-Key must be ≤255 chars"}',
                    status_code=422,
                    media_type="application/json",
                )

        response = await call_next(request)
        return response
