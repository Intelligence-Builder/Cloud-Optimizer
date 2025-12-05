"""Tests for AWS Connection service."""

from __future__ import annotations

import os
import urllib.request
from types import SimpleNamespace
from uuid import UUID, uuid4

import boto3
import pytest
from cryptography.fernet import Fernet

from cloud_optimizer.models.aws_account import ConnectionStatus, ConnectionType
from cloud_optimizer.services.aws_connection import AWSConnectionService

USE_REAL_AWS = os.getenv("USE_REAL_AWS", "false").lower() == "true"
LOCALSTACK_ENDPOINT = os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")


class _EndpointSession(boto3.session.Session):
    """boto3 session that automatically targets LocalStack."""

    def __init__(self, endpoint_url: str, **kwargs):
        super().__init__(**kwargs)
        self._endpoint_url = endpoint_url

    def client(self, service_name: str, **kwargs):
        kwargs.setdefault("endpoint_url", self._endpoint_url)
        return super().client(service_name, **kwargs)


def _localstack_available() -> bool:
    try:
        urllib.request.urlopen(f"{LOCALSTACK_ENDPOINT}/_localstack/health", timeout=5)
        return True
    except Exception:
        return False


@pytest.fixture
def encryption_key() -> str:
    """Provide a deterministic encryption key for service tests."""
    return Fernet.generate_key().decode()


@pytest.fixture
def settings_factory(encryption_key: str):
    """Factory that returns minimal settings objects."""

    def _factory(trial_mode: bool = False):
        return SimpleNamespace(encryption_key=encryption_key, trial_mode=trial_mode)

    return _factory


@pytest.fixture(scope="session")
def aws_backend():
    """Ensure either LocalStack or real AWS is available."""
    if USE_REAL_AWS:
        return {"type": "aws"}
    if _localstack_available():
        return {"type": "localstack"}
    pytest.skip(
        "LocalStack not running and USE_REAL_AWS is false; cannot run AWS connection tests"
    )


@pytest.fixture(scope="session")
def boto_factories(aws_backend):
    """Provide boto3 factories that hit the configured backend."""

    def client_factory(service: str):
        kwargs = {"region_name": AWS_REGION}
        if aws_backend["type"] == "localstack":
            kwargs.update(
                endpoint_url=LOCALSTACK_ENDPOINT,
                aws_access_key_id="test",
                aws_secret_access_key="test",
            )
        return boto3.client(service, **kwargs)

    def session_factory(**kwargs):
        params = dict(kwargs)
        params.setdefault("region_name", AWS_REGION)
        if aws_backend["type"] == "localstack":
            params.setdefault("aws_access_key_id", "test")
            params.setdefault("aws_secret_access_key", "test")
            return _EndpointSession(LOCALSTACK_ENDPOINT, **params)
        return boto3.session.Session(**params)

    return client_factory, session_factory


def _create_service(
    db_session,
    settings_factory,
    boto_factories,
    *,
    trial_mode: bool = False,
) -> AWSConnectionService:
    client_factory, session_factory = boto_factories
    return AWSConnectionService(
        db_session,
        settings=settings_factory(trial_mode),
        boto3_client_factory=client_factory,
        boto3_session_factory=session_factory,
    )


@pytest.mark.asyncio
async def test_connect_with_keys_enforces_encryption(
    db_session, test_user, settings_factory, boto_factories
):
    """Connecting with keys should store encrypted credentials and derive account ID."""
    service = _create_service(db_session, settings_factory, boto_factories)

    account = await service.connect_with_keys(
        user_id=test_user.user_id,
        access_key_id="AKIAEXAMPLE12345",
        secret_access_key="top-secret",
        friendly_name="My Account",
    )

    assert account.connection_type == ConnectionType.ACCESS_KEYS
    assert account.aws_account_id is not None
    assert account.aws_account_id.isdigit()
    assert len(account.aws_account_id) == 12
    assert account.access_key_encrypted is not None
    assert account.secret_key_encrypted is not None

    decrypted = service.fernet.decrypt(account.access_key_encrypted).decode()
    assert decrypted == "AKIAEXAMPLE12345"


@pytest.mark.asyncio
async def test_trial_limit_enforced(
    db_session, test_user, settings_factory, boto_factories
):
    """Trial mode should limit users to a single connected account."""
    service = _create_service(
        db_session, settings_factory, boto_factories, trial_mode=True
    )

    await service.connect_with_keys(
        user_id=test_user.user_id,
        access_key_id="AKIA111111111111",
        secret_access_key="secret-1",
    )

    with pytest.raises(
        ValueError, match="Trial plan allows only one connected AWS account"
    ):
        await service.connect_with_keys(
            user_id=test_user.user_id,
            access_key_id="AKIA222222222222",
            secret_access_key="secret-2",
        )


@pytest.mark.asyncio
async def test_disconnect_clears_credentials(
    db_session, test_user, settings_factory, boto_factories
):
    """Disconnection should clear stored credentials and update status."""
    service = _create_service(db_session, settings_factory, boto_factories)
    account = await service.connect_with_keys(
        user_id=test_user.user_id,
        access_key_id="AKIAAAAAAAAAAAAA",
        secret_access_key="secret",
    )

    await service.disconnect_account(account.account_id, test_user.user_id)

    refreshed = await service.get_account_for_user(
        account.account_id, test_user.user_id
    )
    assert refreshed.status == ConnectionStatus.DISCONNECTED
    assert refreshed.access_key_encrypted is None
    assert refreshed.secret_key_encrypted is None


@pytest.mark.asyncio
async def test_validate_account_updates_status(
    db_session, test_user, settings_factory, boto_factories
):
    """Validation should update timestamps and clear error state."""
    service = _create_service(db_session, settings_factory, boto_factories)
    account = await service.connect_with_keys(
        user_id=test_user.user_id,
        access_key_id="AKIAAAAAAAAAAAAA",
        secret_access_key="secret",
    )

    # Simulate error state
    account.status = ConnectionStatus.ERROR
    account.last_error = "Previous failure"
    await db_session.commit()

    validated = await service.validate_account(account.account_id, test_user.user_id)

    assert validated.status == ConnectionStatus.ACTIVE
    assert validated.last_error is None
    assert validated.last_validated_at is not None


@pytest.mark.asyncio
async def test_connect_with_role_rejects_mismatched_ids(
    db_session, test_user, settings_factory, boto_factories
):
    """Provided account ID must match the role ARN."""
    service = _create_service(db_session, settings_factory, boto_factories)

    with pytest.raises(ValueError):
        await service.connect_with_role(
            user_id=test_user.user_id,
            role_arn="arn:aws:iam::123456789012:role/TestRole",
            aws_account_id="000000000000",
        )
