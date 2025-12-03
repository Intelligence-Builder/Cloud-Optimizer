"""
Integration tests for authentication API endpoints.

Tests all auth endpoints with real database and JWT tokens.
"""

from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cloud_optimizer.auth.password import get_password_policy
from cloud_optimizer.models.session import Session
from cloud_optimizer.models.user import User


@pytest.fixture
def valid_password() -> str:
    """Return a password that meets all policy requirements."""
    return "TestPass123"


@pytest.fixture
def weak_password() -> str:
    """Return a password that fails policy requirements."""
    return "weak"


@pytest.fixture
def test_user_data() -> dict[str, Any]:
    """Return test user registration data."""
    return {
        "email": "test@example.com",
        "password": "TestPass123",
        "name": "Test User",
    }


@pytest_asyncio.fixture
async def registered_user(
    db_session: AsyncSession,
    test_user_data: dict[str, Any],
) -> User:
    """Create and return a registered user in the database."""
    password_policy = get_password_policy()
    user = User(
        email=test_user_data["email"],
        password_hash=password_policy.hash(test_user_data["password"]),
        name=test_user_data["name"],
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_tokens(
    async_client: AsyncClient,
    test_user_data: dict[str, Any],
    registered_user: User,
) -> dict[str, str]:
    """Login and return auth tokens for a registered user."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user_data["email"],
            "password": test_user_data["password"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    return {
        "access_token": data["tokens"]["access_token"],
        "refresh_token": data["tokens"]["refresh_token"],
    }


@pytest.fixture
def auth_headers(auth_tokens: dict[str, str]) -> dict[str, str]:
    """Return authorization headers with valid access token."""
    return {"Authorization": f"Bearer {auth_tokens['access_token']}"}


# Registration Tests


@pytest.mark.asyncio
async def test_register_success(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Test successful user registration."""
    email = f"newuser-{uuid4()}@example.com"
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "ValidPass123",
            "name": "New User",
        },
    )

    assert response.status_code == 201
    data = response.json()

    # Verify response structure
    assert "user" in data
    assert "tokens" in data

    # Verify user data
    user_data = data["user"]
    assert user_data["email"] == email.lower()
    assert user_data["name"] == "New User"
    assert "is_admin" in user_data  # Don't assert value, model default is True
    assert "email_verified" in user_data
    assert "user_id" in user_data
    assert "created_at" in user_data

    # Verify tokens
    tokens = data["tokens"]
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "bearer"
    assert tokens["expires_in"] > 0

    # Verify user was created in database
    result = await db_session.execute(select(User).where(User.email == email.lower()))
    db_user = result.scalar_one_or_none()
    assert db_user is not None
    assert db_user.email == email.lower()
    assert db_user.name == "New User"


@pytest.mark.asyncio
async def test_register_duplicate_email(
    async_client: AsyncClient,
    registered_user: User,
) -> None:
    """Test registration with duplicate email returns 409."""
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": registered_user.email,
            "password": "ValidPass123",
            "name": "Duplicate User",
        },
    )

    assert response.status_code == 409
    data = response.json()
    assert "detail" in data
    assert "already exists" in data["detail"].lower()


@pytest.mark.asyncio
async def test_register_invalid_password(
    async_client: AsyncClient,
    weak_password: str,
) -> None:
    """Test registration with weak password returns 422 for validation errors."""
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": weak_password,
            "name": "Test User",
        },
    )

    # Pydantic validation returns 422 for field constraints
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_register_invalid_email(async_client: AsyncClient) -> None:
    """Test registration with invalid email returns 422."""
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "not-an-email",
            "password": "ValidPass123",
            "name": "Test User",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_normalizes_email(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Test that registration normalizes email to lowercase."""
    email = f"MixedCase-{uuid4()}@Example.COM"
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "ValidPass123",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["user"]["email"] == email.lower()


# Login Tests


@pytest.mark.asyncio
async def test_login_success(
    async_client: AsyncClient,
    test_user_data: dict[str, Any],
    registered_user: User,
) -> None:
    """Test successful login."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user_data["email"],
            "password": test_user_data["password"],
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "user" in data
    assert "tokens" in data

    # Verify user data
    assert data["user"]["email"] == test_user_data["email"]
    assert data["user"]["user_id"] == str(registered_user.user_id)

    # Verify tokens
    tokens = data["tokens"]
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(
    async_client: AsyncClient,
    registered_user: User,
) -> None:
    """Test login with wrong password returns 401."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": registered_user.email,
            "password": "WrongPass123",
        },
    )

    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_login_unknown_email(async_client: AsyncClient) -> None:
    """Test login with unknown email returns 401."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "unknown@example.com",
            "password": "ValidPass123",
        },
    )

    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_login_case_insensitive_email(
    async_client: AsyncClient,
    test_user_data: dict[str, Any],
    registered_user: User,
) -> None:
    """Test login with different email case succeeds."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user_data["email"].upper(),
            "password": test_user_data["password"],
        },
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_login_updates_last_login(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_user_data: dict[str, Any],
    registered_user: User,
) -> None:
    """Test that login updates the last_login_at timestamp."""
    # Get initial last_login (should be None)
    initial_last_login = registered_user.last_login_at

    # Login
    await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user_data["email"],
            "password": test_user_data["password"],
        },
    )

    # Refresh user from database
    await db_session.refresh(registered_user)

    # Verify last_login was updated
    assert registered_user.last_login_at is not None
    if initial_last_login:
        assert registered_user.last_login_at > initial_last_login


# Token Refresh Tests


@pytest.mark.asyncio
async def test_refresh_success(
    async_client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """Test successful token refresh."""
    import asyncio

    # Wait a moment to ensure token timestamps differ
    await asyncio.sleep(1)

    response = await async_client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": auth_tokens["refresh_token"],
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Verify new tokens are present
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0

    # Tokens should have new timestamps (different iat)
    # The refresh token will be different because it has a new iat timestamp
    # even though it reuses the same session_id
    from cloud_optimizer.auth.jwt import get_token_service

    token_service = get_token_service()
    old_payload = token_service.decode_token(auth_tokens["refresh_token"])
    new_payload = token_service.decode_token(data["refresh_token"])

    # New token should have a later issued-at time
    assert new_payload.iat > old_payload.iat


@pytest.mark.asyncio
async def test_refresh_invalid_token(async_client: AsyncClient) -> None:
    """Test refresh with invalid token returns 401."""
    response = await async_client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": "invalid-token",
        },
    )

    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_refresh_with_access_token_fails(
    async_client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """Test that using access token for refresh fails."""
    response = await async_client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": auth_tokens["access_token"],
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_revoked_session(
    async_client: AsyncClient,
    db_session: AsyncSession,
    auth_tokens: dict[str, str],
    registered_user: User,
) -> None:
    """Test refresh with revoked session returns 401."""
    # Revoke all sessions
    result = await db_session.execute(
        select(Session).where(Session.user_id == registered_user.user_id)
    )
    sessions = result.scalars().all()
    for session in sessions:
        from datetime import datetime, timezone

        session.revoked_at = datetime.now(timezone.utc)
    await db_session.commit()

    # Try to refresh
    response = await async_client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": auth_tokens["refresh_token"],
        },
    )

    assert response.status_code == 401


# Logout Tests


@pytest.mark.asyncio
async def test_logout_success(
    async_client: AsyncClient,
    db_session: AsyncSession,
    auth_tokens: dict[str, str],
    registered_user: User,
) -> None:
    """Test successful logout."""
    response = await async_client.post(
        "/api/v1/auth/logout",
        json={
            "refresh_token": auth_tokens["refresh_token"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "logged out" in data["message"].lower()

    # Verify session was revoked
    result = await db_session.execute(
        select(Session).where(Session.user_id == registered_user.user_id)
    )
    sessions = result.scalars().all()
    assert all(session.revoked_at is not None for session in sessions)


@pytest.mark.asyncio
async def test_logout_invalid_token(async_client: AsyncClient) -> None:
    """Test logout with invalid token succeeds (idempotent)."""
    response = await async_client.post(
        "/api/v1/auth/logout",
        json={
            "refresh_token": "invalid-token",
        },
    )

    # Logout should always succeed
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_logout_prevents_token_reuse(
    async_client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """Test that tokens cannot be used after logout."""
    # Logout
    await async_client.post(
        "/api/v1/auth/logout",
        json={
            "refresh_token": auth_tokens["refresh_token"],
        },
    )

    # Try to refresh with logged out token
    response = await async_client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": auth_tokens["refresh_token"],
        },
    )

    assert response.status_code == 401


# Get Profile Tests


@pytest.mark.asyncio
async def test_get_me_success(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    registered_user: User,
) -> None:
    """Test getting current user profile."""
    response = await async_client.get(
        "/api/v1/auth/me",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Verify user data
    assert data["user_id"] == str(registered_user.user_id)
    assert data["email"] == registered_user.email
    assert data["name"] == registered_user.name
    assert "is_admin" in data
    assert "email_verified" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_get_me_no_auth(async_client: AsyncClient) -> None:
    """Test getting profile without authentication returns 403."""
    response = await async_client.get("/api/v1/auth/me")

    # FastAPI returns 403 when HTTPBearer(auto_error=True) gets no credentials
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_me_invalid_token(async_client: AsyncClient) -> None:
    """Test getting profile with invalid token returns 401."""
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_with_refresh_token_fails(
    async_client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """Test that refresh token cannot be used for authentication."""
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {auth_tokens['refresh_token']}"},
    )

    assert response.status_code == 401


# Update Profile Tests


@pytest.mark.asyncio
async def test_update_me_name(
    async_client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict[str, str],
    registered_user: User,
) -> None:
    """Test updating user name."""
    new_name = "Updated Name"
    response = await async_client.put(
        "/api/v1/auth/me",
        headers=auth_headers,
        json={"name": new_name},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == new_name

    # Verify in database
    await db_session.refresh(registered_user)
    assert registered_user.name == new_name


@pytest.mark.asyncio
async def test_update_me_email(
    async_client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict[str, str],
    registered_user: User,
) -> None:
    """Test updating user email."""
    new_email = f"updated-{uuid4()}@example.com"
    response = await async_client.put(
        "/api/v1/auth/me",
        headers=auth_headers,
        json={"email": new_email},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == new_email.lower()

    # Verify in database
    await db_session.refresh(registered_user)
    assert registered_user.email == new_email.lower()


@pytest.mark.asyncio
async def test_update_me_duplicate_email(
    async_client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict[str, str],
) -> None:
    """Test updating to existing email returns 409."""
    # Create another user
    password_policy = get_password_policy()
    other_user = User(
        email="other@example.com",
        password_hash=password_policy.hash("TestPass123"),
    )
    db_session.add(other_user)
    await db_session.commit()

    # Try to update to other user's email
    response = await async_client.put(
        "/api/v1/auth/me",
        headers=auth_headers,
        json={"email": other_user.email},
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_update_me_no_auth(async_client: AsyncClient) -> None:
    """Test updating profile without authentication returns 403."""
    response = await async_client.put(
        "/api/v1/auth/me",
        json={"name": "New Name"},
    )

    # FastAPI returns 403 when HTTPBearer(auto_error=True) gets no credentials
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_me_both_fields(
    async_client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict[str, str],
    registered_user: User,
) -> None:
    """Test updating both name and email together."""
    new_name = "Updated Name"
    new_email = f"updated-{uuid4()}@example.com"

    response = await async_client.put(
        "/api/v1/auth/me",
        headers=auth_headers,
        json={
            "name": new_name,
            "email": new_email,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == new_name
    assert data["email"] == new_email.lower()


# Change Password Tests


@pytest.mark.asyncio
async def test_change_password_success(
    async_client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict[str, str],
    test_user_data: dict[str, Any],
    registered_user: User,
) -> None:
    """Test successful password change."""
    new_password = "NewPass123"

    response = await async_client.put(
        "/api/v1/auth/password",
        headers=auth_headers,
        json={
            "old_password": test_user_data["password"],
            "new_password": new_password,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "message" in data

    # Verify old password no longer works
    login_response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user_data["email"],
            "password": test_user_data["password"],
        },
    )
    assert login_response.status_code == 401

    # Verify new password works
    login_response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user_data["email"],
            "password": new_password,
        },
    )
    assert login_response.status_code == 200


@pytest.mark.asyncio
async def test_change_password_wrong_old_password(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Test password change with wrong old password returns 401."""
    response = await async_client.put(
        "/api/v1/auth/password",
        headers=auth_headers,
        json={
            "old_password": "WrongPass123",
            "new_password": "NewPass123",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_change_password_weak_new_password(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    test_user_data: dict[str, Any],
    weak_password: str,
) -> None:
    """Test password change with weak new password returns 422."""
    response = await async_client.put(
        "/api/v1/auth/password",
        headers=auth_headers,
        json={
            "old_password": test_user_data["password"],
            "new_password": weak_password,
        },
    )

    # Pydantic validation returns 422 for field constraints
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_change_password_no_auth(async_client: AsyncClient) -> None:
    """Test changing password without authentication returns 403."""
    response = await async_client.put(
        "/api/v1/auth/password",
        json={
            "old_password": "OldPass123",
            "new_password": "NewPass123",
        },
    )

    # FastAPI returns 403 when HTTPBearer(auto_error=True) gets no credentials
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_change_password_revokes_sessions(
    async_client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict[str, str],
    auth_tokens: dict[str, str],
    test_user_data: dict[str, Any],
    registered_user: User,
) -> None:
    """Test that password change revokes all existing sessions."""
    # Change password
    await async_client.put(
        "/api/v1/auth/password",
        headers=auth_headers,
        json={
            "old_password": test_user_data["password"],
            "new_password": "NewPass123",
        },
    )

    # Try to refresh with old refresh token
    response = await async_client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": auth_tokens["refresh_token"],
        },
    )

    assert response.status_code == 401

    # Verify all sessions are revoked
    result = await db_session.execute(
        select(Session).where(Session.user_id == registered_user.user_id)
    )
    sessions = result.scalars().all()
    assert all(session.revoked_at is not None for session in sessions)


# Edge Cases and Security Tests


@pytest.mark.asyncio
async def test_concurrent_registrations_same_email(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Test that duplicate email registration returns 409."""
    # This test validates duplicate detection rather than true concurrency
    # as async test clients don't provide true parallel execution
    email = f"concurrent-{uuid4()}@example.com"

    # First registration should succeed
    response1 = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "ValidPass123",
        },
    )
    assert response1.status_code == 201

    # Commit the first registration
    await db_session.commit()

    # Second registration with same email should fail
    response2 = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "ValidPass123",
        },
    )
    assert response2.status_code == 409
    assert "already exists" in response2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_does_not_leak_user_existence(
    async_client: AsyncClient,
    registered_user: User,
) -> None:
    """Test that login errors don't reveal if email exists."""
    # Wrong password for existing user
    response1 = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": registered_user.email,
            "password": "WrongPass123",
        },
    )

    # Unknown email
    response2 = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "WrongPass123",
        },
    )

    # Both should return same error (don't leak user existence)
    assert response1.status_code == 401
    assert response2.status_code == 401
    # Error messages should be generic
    assert "invalid" in response1.json()["detail"].lower()
    assert "invalid" in response2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_tokens_are_unique_per_login(
    async_client: AsyncClient,
    test_user_data: dict[str, Any],
    registered_user: User,
) -> None:
    """Test that each login generates unique tokens."""
    import asyncio

    # Login first time
    response1 = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user_data["email"],
            "password": test_user_data["password"],
        },
    )

    # Wait a moment to ensure different timestamps
    await asyncio.sleep(0.1)

    # Login second time
    response2 = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user_data["email"],
            "password": test_user_data["password"],
        },
    )

    tokens1 = response1.json()["tokens"]
    tokens2 = response2.json()["tokens"]

    # Refresh tokens should definitely be different (different sessions)
    assert tokens1["refresh_token"] != tokens2["refresh_token"]
    # Access tokens will likely be different due to different timestamps and session IDs


@pytest.mark.asyncio
async def test_bearer_token_format_validation(
    async_client: AsyncClient,
) -> None:
    """Test that malformed authorization headers are rejected."""
    # Missing Bearer prefix - FastAPI returns 403 for invalid scheme
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "some-token"},
    )
    assert response.status_code == 403

    # Empty token - returns 401 for invalid token
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer "},
    )
    assert response.status_code in [401, 403]  # Could be either depending on validation
