"""Pytest fixtures for marketplace tests."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


@pytest.fixture
def mock_boto3_client():
    """Mock boto3 client for marketplace API."""
    with patch('boto3.client') as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


@pytest.fixture
def valid_subscription_client(mock_boto3_client):
    """Mock client with valid subscription."""
    mock_boto3_client.register_usage.return_value = {
        "CustomerIdentifier": "customer-123",
        "Signature": "signature",
    }
    return mock_boto3_client


@pytest.fixture
def expired_subscription_client(mock_boto3_client):
    """Mock client with expired subscription."""
    from botocore.exceptions import ClientError
    error_response = {'Error': {'Code': 'CustomerNotSubscribedException', 'Message': 'test'}}
    mock_boto3_client.register_usage.side_effect = ClientError(error_response, 'RegisterUsage')
    return mock_boto3_client


@pytest.fixture
def trial_client(mock_boto3_client):
    """Mock client with trial status."""
    from botocore.exceptions import ClientError
    error_response = {'Error': {'Code': 'CustomerNotEntitledException', 'Message': 'test'}}
    mock_boto3_client.register_usage.side_effect = ClientError(error_response, 'RegisterUsage')
    return mock_boto3_client
