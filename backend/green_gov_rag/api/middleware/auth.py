"""API authentication middleware.

Protects all API endpoints by requiring an API access key in the request headers.
"""

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware

from green_gov_rag.config import settings


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce API key authentication for all endpoints.

    This middleware checks for the X-API-Key header in all requests
    (except health checks) and validates it against the configured API_ACCESS_KEY.

    Usage:
        app.add_middleware(APIKeyAuthMiddleware)
    """

    async def dispatch(self, request: Request, call_next):
        """Process the request and validate API key.

        Args:
            request: The incoming request
            call_next: The next middleware/handler in the chain

        Returns:
            Response from the next handler if authentication succeeds

        Raises:
            HTTPException: 403 Forbidden if API key is missing or invalid
        """
        # Skip authentication for health check endpoint
        if request.url.path == "/api/health":
            return await call_next(request)

        # Skip authentication for docs in development
        if settings.app_env == "development" and request.url.path in [
            "/docs",
            "/redoc",
            "/openapi.json",
        ]:
            return await call_next(request)

        # Check for API key in headers (try both X-API-Key and X-Api-Key)
        api_key = request.headers.get("X-API-Key") or request.headers.get("X-Api-Key")

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Missing API access key. Include X-API-Key header in your request.",
            )

        # Check if this is an admin route
        if request.url.path.startswith("/api/admin/"):
            # Admin routes require admin API key
            if not settings.admin_api_key:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin API key not configured. Contact system administrator.",
                )

            if api_key != settings.admin_api_key:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid admin API key. Admin access denied.",
                )
        else:
            # Regular API routes require regular API key
            if api_key != settings.api_access_key:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid API access key",
                )

        # API key is valid, proceed with request
        return await call_next(request)
