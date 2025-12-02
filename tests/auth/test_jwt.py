"""Tests for JWT token service."""

from uuid import uuid4

import pytest

from cloud_optimizer.auth.jwt import (
    TokenError,
    TokenPair,
    TokenPayload,
    TokenService,
    get_token_service,
)


class TestTokenService:
    """Tests for TokenService class."""

    def setup_method(self) -> None:
        """Setup test fixtures."""
        self.service = TokenService()
        self.user_id = uuid4()
        self.session_id = uuid4()

    def test_create_access_token(self) -> None:
        """Test access token creation."""
        token = self.service.create_access_token(self.user_id)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self) -> None:
        """Test refresh token creation."""
        token = self.service.create_refresh_token(self.user_id, self.session_id)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_token_pair(self) -> None:
        """Test token pair creation."""
        pair = self.service.create_token_pair(self.user_id, self.session_id)
        assert isinstance(pair, TokenPair)
        assert pair.access_token
        assert pair.refresh_token
        assert pair.token_type == "bearer"
        assert pair.expires_in > 0

    def test_decode_access_token(self) -> None:
        """Test decoding valid access token."""
        token = self.service.create_access_token(self.user_id)
        payload = self.service.decode_token(token)
        assert isinstance(payload, TokenPayload)
        assert payload.sub == str(self.user_id)
        assert payload.token_type == "access"

    def test_decode_refresh_token(self) -> None:
        """Test decoding valid refresh token."""
        token = self.service.create_refresh_token(self.user_id, self.session_id)
        payload = self.service.decode_token(token)
        assert isinstance(payload, TokenPayload)
        assert payload.sub == str(self.user_id)
        assert payload.token_type == "refresh"
        assert payload.jti == str(self.session_id)

    def test_validate_access_token_success(self) -> None:
        """Test validating correct access token type."""
        token = self.service.create_access_token(self.user_id)
        payload = self.service.validate_access_token(token)
        assert payload.token_type == "access"

    def test_validate_access_token_wrong_type(self) -> None:
        """Test validating refresh token as access token fails."""
        token = self.service.create_refresh_token(self.user_id, self.session_id)
        with pytest.raises(TokenError, match="not an access token"):
            self.service.validate_access_token(token)

    def test_validate_refresh_token_success(self) -> None:
        """Test validating correct refresh token type."""
        token = self.service.create_refresh_token(self.user_id, self.session_id)
        payload = self.service.validate_refresh_token(token)
        assert payload.token_type == "refresh"
        assert payload.jti == str(self.session_id)

    def test_validate_refresh_token_wrong_type(self) -> None:
        """Test validating access token as refresh token fails."""
        token = self.service.create_access_token(self.user_id)
        with pytest.raises(TokenError, match="not a refresh token"):
            self.service.validate_refresh_token(token)

    def test_decode_invalid_token(self) -> None:
        """Test decoding invalid token raises error."""
        with pytest.raises(TokenError, match="Invalid token"):
            self.service.decode_token("invalid.token.here")

    def test_decode_malformed_token(self) -> None:
        """Test decoding malformed token raises error."""
        with pytest.raises(TokenError):
            self.service.decode_token("notavalidjwt")

    def test_get_user_id_from_token(self) -> None:
        """Test extracting user ID from token."""
        token = self.service.create_access_token(self.user_id)
        extracted_id = self.service.get_user_id_from_token(token)
        assert extracted_id == self.user_id

    def test_access_token_with_extra_claims(self) -> None:
        """Test access token with extra claims."""
        extra = {"role": "admin", "tenant_id": "test"}
        token = self.service.create_access_token(self.user_id, extra_claims=extra)
        # Token should still be valid
        payload = self.service.validate_access_token(token)
        assert payload.sub == str(self.user_id)


class TestTokenServiceSingleton:
    """Tests for token service singleton."""

    def test_get_token_service_returns_instance(self) -> None:
        """Test that get_token_service returns an instance."""
        service = get_token_service()
        assert isinstance(service, TokenService)

    def test_get_token_service_returns_same_instance(self) -> None:
        """Test that get_token_service returns same instance."""
        service1 = get_token_service()
        service2 = get_token_service()
        assert service1 is service2
