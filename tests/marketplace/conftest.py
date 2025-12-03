"""
Pytest fixtures for marketplace tests.

IMPORTANT NOTES:
- AWS Marketplace Metering API is NOT supported by LocalStack
- These fixtures provide minimal setup for testing marketplace code
- Most tests use direct unit/integration testing without AWS dependencies
- For real marketplace testing, use AWS test accounts with proper IAM policies

See localstack_conftest.py for LocalStack-specific fixtures (S3, IAM, etc.)
"""

import pytest


# This file intentionally minimal - fixtures moved to test files
# to keep test dependencies clear and avoid mock complexity.
#
# Previous mock fixtures removed in favor of:
# 1. Direct unit tests (test internal logic)
# 2. Integration tests with TestClient (test middleware behavior)
# 3. Real AWS tests (marked with @pytest.mark.real_aws)
