# Marketplace Tests

This directory contains tests for AWS Marketplace integration features including license validation, usage metering, and license enforcement middleware.

## Testing Strategy

### AWS Marketplace API Limitations

**CRITICAL:** AWS Marketplace Metering API is **NOT supported by LocalStack** (Community or Pro editions as of December 2025).

Due to this limitation, we employ a hybrid testing approach:

### 1. Unit Tests (`@pytest.mark.unit`)
- Test internal logic without AWS dependencies
- Focus on: caching, buffering, aggregation, state management
- No mocks required - test pure functions
- Fast execution, run on every commit

### 2. Integration Tests (`@pytest.mark.integration`)
- Test component interactions with mocked AWS clients
- Use `MagicMock` for boto3 clients only when testing AWS API interactions
- Use real `FastAPI.TestClient` for middleware testing
- Test error handling, retries, graceful degradation
- Validate request/response flows

### 3. LocalStack Tests (`@pytest.mark.localstack_only`)
- Currently skipped due to marketplace API unavailability
- Fixtures available in `localstack_conftest.py` for S3, IAM, CloudWatch
- Placeholder tests ready for when LocalStack adds marketplace support

### 4. Real AWS Tests (`@pytest.mark.real_aws`)
- Require valid AWS credentials
- Test against actual AWS Marketplace APIs
- **Manually enabled only** - never run in CI/CD
- Require environment variable: `TEST_MARKETPLACE_PRODUCT_CODE`

## Test Files

### `test_license.py`
Tests for `MarketplaceLicenseValidator` class:
- License status validation (valid, trial, expired)
- Customer identification
- Status caching (1-hour TTL)
- Error handling (network failures, invalid responses)
- Singleton pattern

**Test Coverage:** 14 tests (54 passed total with metering and middleware)

### `test_middleware.py`
Tests for `LicenseMiddleware` class:
- Public endpoint bypass (health, docs, etc.)
- License enforcement on API endpoints
- HTTP 402 responses for expired licenses
- Graceful degradation for invalid status
- Path matching and routing
- Dynamic status changes

**Test Coverage:** 20 tests (all real integration tests)

### `test_metering.py`
Tests for `UsageMeteringService` class:
- Usage recording and buffering
- Automatic flush at threshold (10 records)
- Manual flush operations
- Dimension aggregation
- Retry logic for failed sends
- Service lifecycle (start/stop)

**Test Coverage:** 22 tests

### `conftest.py`
Minimal fixture file - fixtures moved to test files for clarity.

### `localstack_conftest.py`
LocalStack fixtures for AWS services:
- S3 client with cleanup
- IAM client
- CloudWatch client
- Wait-for-ready helpers
- Documentation for marketplace limitations

## Running Tests

### Run all marketplace tests:
```bash
pytest tests/marketplace/ -v
```

### Run only unit tests (no AWS):
```bash
pytest tests/marketplace/ -m unit -v
```

### Run only integration tests:
```bash
pytest tests/marketplace/ -m integration -v
```

### Run specific test file:
```bash
pytest tests/marketplace/test_license.py -v
pytest tests/marketplace/test_middleware.py -v
pytest tests/marketplace/test_metering.py -v
```

### Run with coverage:
```bash
pytest tests/marketplace/ --cov=cloud_optimizer.marketplace --cov-report=html
```

### Enable real AWS tests (manual only):
```bash
export TEST_MARKETPLACE_PRODUCT_CODE=your-product-code
pytest tests/marketplace/ -m real_aws -v
```

## Test Results Summary

As of December 2025:
- **54 tests passed**
- **4 tests skipped** (LocalStack + Real AWS placeholders)
- **0 tests failed**
- **Test execution time:** ~0.56 seconds

## Key Testing Principles

### 1. Real Integration Over Mocks
- Middleware tests use real `TestClient` with actual HTTP requests
- Only mock boto3 clients for AWS API calls (unavoidable)
- Test actual code paths, not mock behavior

### 2. Clear Test Organization
- Tests grouped by functionality with comment headers
- Each test has descriptive docstring
- Test names clearly indicate what's being tested

### 3. Type Safety
- All test functions have proper type hints
- Use `-> None` for test functions
- Mock objects typed where possible

### 4. Comprehensive Coverage
- Happy path tests
- Error condition tests
- Edge case tests
- Performance tests (buffering, caching)

## Future Enhancements

### When LocalStack Adds Marketplace Support:
1. Remove `@pytest.mark.skip` decorators from LocalStack tests
2. Implement real HTTP-based integration tests
3. Test against mock marketplace endpoints
4. Validate complete request/response cycles

### Alternative Approaches:
1. **Custom Mock Server**: Implement FastAPI app simulating marketplace API
2. **AWS Test Accounts**: Use dedicated AWS accounts with test products
3. **Contract Testing**: Use Pact or similar for API contract validation

## Dependencies

Required packages:
- `pytest>=7.4.0`
- `pytest-asyncio>=0.21.0`
- `pytest-cov>=4.1.0`
- `fastapi>=0.104.0`
- `boto3>=1.33.0`
- `botocore>=1.33.0`

Optional for LocalStack:
- `docker>=7.0.0`
- `requests>=2.31.0`

## CI/CD Integration

These tests are safe for CI/CD:
- No external AWS dependencies
- Fast execution (<1 second)
- No LocalStack container required
- Deterministic results

Skipped tests:
- `@pytest.mark.localstack_only` - Require LocalStack container
- `@pytest.mark.real_aws` - Require AWS credentials

## Troubleshooting

### Tests fail with "fixture not found"
- Ensure pytest is discovering all fixture files
- Check that conftest.py files are in the correct directories

### AsyncIO errors
- Ensure `pytest-asyncio` is installed
- Check `pyproject.toml` has `asyncio_mode = "auto"`

### Import errors
- Ensure project root is in PYTHONPATH
- Run tests from project root directory
- Check that `src/` directory structure is correct

## References

- [AWS Marketplace Metering API Documentation](https://docs.aws.amazon.com/marketplace/latest/APIReference/API_Types_AWSMarketplace_Metering.html)
- [LocalStack Service Coverage](https://docs.localstack.cloud/aws/services/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [FastAPI Testing Guide](https://fastapi.tiangolo.com/tutorial/testing/)

## Contact

For questions about marketplace testing:
- Review implementation in `src/cloud_optimizer/marketplace/`
- Check project CLAUDE.md for testing guidelines
- See QUALITY_FIRST_CODING_TEMPLATE.md for coding standards
