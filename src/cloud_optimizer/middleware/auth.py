"""
Authentication middleware for Cloud Optimizer.

Provides JWT token validation and user extraction from requests.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from cloud_optimizer.auth.jwt import TokenError, get_token_service

# Module-level security schemes to avoid B008 warnings
_optional_bearer = HTTPBearer(auto_error=False)
_required_bearer = HTTPBearer(auto_error=True)


class AuthMiddleware:
    """
    Authentication middleware.

    Extracts and validates Bearer tokens from Authorization header.
    Injects user_id into request state.
    """

    def __init__(self) -> None:
        """Initialize middleware."""
        self.security = _optional_bearer
        self.token_service = get_token_service()

    async def __call__(
        self,
        request: Request,
        credentials: HTTPAuthorizationCredentials
        | None = Depends(_optional_bearer),  # noqa: B008
    ) -> UUID | None:
        """
        Extract and validate token from request.

        Args:
            request: FastAPI request object.
            credentials: Optional Bearer token credentials.

        Returns:
            User ID if valid token, None otherwise.
        """
        if not credentials:
            return None

        try:
            payload = self.token_service.validate_access_token(credentials.credentials)
            user_id = UUID(payload.sub)

            # Store in request state for later access
            request.state.user_id = user_id
            return user_id
        except (TokenError, ValueError):
            return None


# Dependency for optional auth (doesn't require token)
_auth_middleware = AuthMiddleware()


async def get_current_user_optional(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_optional_bearer),
    ] = None,
) -> UUID | None:
    """
    Dependency for optional authentication.

    Returns user_id if valid token provided, None otherwise.
    Does not raise error for missing/invalid token.
    """
    if not credentials:
        return None

    token_service = get_token_service()

    try:
        payload = token_service.validate_access_token(credentials.credentials)
        user_id = UUID(payload.sub)
        request.state.user_id = user_id
        return user_id
    except (TokenError, ValueError):
        return None


async def get_current_user(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_required_bearer),
    ],
) -> UUID:
    """
    Dependency for required authentication.

    Returns user_id if valid token provided.
    Raises 401 for missing/invalid token.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_service = get_token_service()

    try:
        payload = token_service.validate_access_token(credentials.credentials)
        user_id = UUID(payload.sub)
        request.state.user_id = user_id
        return user_id
    except TokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


# Type aliases for dependency injection
CurrentUser = Annotated[UUID, Depends(get_current_user)]
CurrentUserOptional = Annotated[UUID | None, Depends(get_current_user_optional)]
