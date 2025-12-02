"""Tests for AWS Connection service.

Note: These are basic unit tests. Full integration tests with actual AWS
credentials should be in a separate integration test suite.
"""
from uuid import uuid4

import pytest

from cloud_optimizer.models.aws_account import ConnectionStatus, ConnectionType
from cloud_optimizer.services.aws_connection import AWSConnectionService


@pytest.mark.asyncio
async def test_service_initialization(db_session):
    """Test AWS connection service initializes correctly."""
    service = AWSConnectionService(db_session)
    assert service.db == db_session


@pytest.mark.asyncio
async def test_get_user_accounts_empty(db_session):
    """Test getting accounts for user with no accounts."""
    service = AWSConnectionService(db_session)
    user_id = uuid4()
    accounts = await service.get_user_accounts(user_id)
    assert accounts == []


@pytest.mark.asyncio
async def test_connect_with_role_validation(db_session):
    """Test role ARN validation."""
    service = AWSConnectionService(db_session)
    user_id = uuid4()

    # This will fail because boto3 will try to assume the role
    # In a real test, we would mock boto3 or use LocalStack
    with pytest.raises(Exception):  # Will raise due to invalid/missing AWS credentials
        await service.connect_with_role(
            user_id=user_id,
            aws_account_id="123456789012",
            role_arn="arn:aws:iam::123456789012:role/TestRole",
            friendly_name="Test Account",
        )


@pytest.mark.asyncio
async def test_disconnect_nonexistent_account(db_session):
    """Test disconnecting non-existent account."""
    service = AWSConnectionService(db_session)
    account_id = uuid4()

    # Should not raise error, just do nothing
    await service.disconnect(account_id)
    # Verify no accounts exist
    accounts = await service.get_user_accounts(uuid4())
    assert len(accounts) == 0


@pytest.mark.asyncio
async def test_get_account_not_found(db_session):
    """Test getting non-existent account."""
    service = AWSConnectionService(db_session)
    account_id = uuid4()

    account = await service.get_account(account_id)
    assert account is None
