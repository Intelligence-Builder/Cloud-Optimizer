# Mock and Stub Usage Inventory

## Purpose
Provide a single reference of source files that currently mention or rely on mocks or stubs so future refactoring or audit work can focus on the right areas without re-running ad-hoc searches.

## Search Method
- Ran on-demand with ripgrep from the repository root (2024-05-07).
- Limited to common code extensions to avoid unrelated markdown hits.

```bash
rg --type-add 'code:*.{py,ts,tsx,js,jsx,sql}' -n -m 1 --type code 'mock|stub' | sort
```

## Summary
- 59 source files contain at least one instance of the words “mock” or “stub”.
- The majority are tests that either import `unittest.mock`, call `vi.mock`, or document that a suite deliberately avoids mocks.
- Only one non-test artefact (`docker/init-test-db.sql`) references stubs, and that reference is a comment about Alembic compatibility.

## File Inventory
- `docker/init-test-db.sql:108` – Commented stub tables included so Alembic can drop legacy structures cleanly.
- `frontend/src/components/chat/__tests__/ChatMessage.test.tsx:6` – Uses a `mockTimestamp` constant inside the chat message snapshot tests.
- `frontend/src/components/document/__tests__/DocumentUpload.test.tsx:8` – Uses `vi.mock` to stub the documents API module.
- `frontend/src/components/trial/__tests__/TrialBanner.test.tsx:7` – Stubs the `useTrial` hook with `vi.mock`.
- `frontend/src/hooks/__tests__/useChat.test.ts:7` – `vi.mock` replaces the chat API to simulate responses.
- `frontend/src/test/setup.ts:12` – Calls `vi.stubEnv` to control `VITE_API_BASE_URL` during tests.
- `frontend/vitest.config.ts:21` – Excludes `mockData` folders from coverage collection.
- `tests/api/test_findings_api.py:3` – Notes that the auth middleware must be mocked or bypassed in these API tests.
- `tests/e2e/conftest.py:10` – Explicitly documents that E2E tests hit real services without mocks.
- `tests/ib_platform/answer/conftest.py:3` – Imports `AsyncMock`/`MagicMock` for fixtures supporting answer service tests.
- `tests/ib_platform/answer/test_context.py:22` – Test signature depends on `mock_kb_service` and `mock_findings_service` fixtures.
- `tests/ib_platform/answer/test_integration.py:18` – Uses multiple mock fixtures for Anthropics, KB, and findings services.
- `tests/ib_platform/answer/test_service.py:12` – Same suite leverages shared mock fixtures to isolate dependencies.
- `tests/ib_platform/answer/test_streaming.py:13` – Streaming tests stitch together mock Anthropics, KB, and findings services.
- `tests/ib_platform/document/test_api.py:10` – Imports `AsyncMock`, `MagicMock`, and `patch` for document API tests.
- `tests/ib_platform/graph/conftest.py:5` – Documentation string stresses no mocks are used (still contains the keyword).
- `tests/ib_platform/graph/test_factory.py:5` – Notes the suite avoids mocks and uses real database connections.
- `tests/ib_platform/graph/test_memgraph.py:5` – Similar “no mocks” disclaimer for Memgraph tests.
- `tests/ib_platform/graph/test_postgres_cte.py:5` – Comment emphasizes real Postgres operations (no mocks).
- `tests/ib_platform/nlu/conftest.py:6` – Imports `Mock` to build fixtures for NLU services.
- `tests/ib_platform/nlu/test_service.py:6` – Uses `Mock` objects inside NLU service unit tests.
- `tests/ib_platform/security/test_explanation.py:3` – Imports `AsyncMock`, `MagicMock`, and `patch` for security explanation tests.
- `tests/integration/test_epic5_ss_integration.py:42` – Warns that this suite is *not* mocked and runs against a database.
- `tests/integration/test_epic6_container.py:6` – States the container suite interacts with Docker/networking without mocks.
- `tests/integration/test_epic8_expert_system.py:5` – Comment clarifies security pattern tests avoid mocks or stubs.
- `tests/integration/test_security_api.py:29` – Imports `AsyncMock` for API security tests.
- `tests/integration/test_ss_cli_workflow.py:5` – Notes the CLI workflow test uses LocalIBService without mocks.
- `tests/marketplace/conftest.py:16` – Explains fixtures prefer real dependencies to keep mock usage low.
- `tests/marketplace/localstack_conftest.py:6` – States tests should use mock servers or real AWS accounts instead of classic mocking.
- `tests/marketplace/test_license.py:7` – Documents integration tests that use a custom mock server to simulate the Marketplace API.
- `tests/marketplace/test_metering.py:7` – Notes mocked AWS clients are used for metering API calls.
- `tests/marketplace/test_middleware.py:6` – Emphasizes HTTP middleware tests avoid mocking request/response flow.
- `tests/qa/conftest.py:178` – Defines `mock_gh_output` helper returning stubbed GitHub CLI output.
- `tests/qa/test_qa_process_shell.py:308` – Comment acknowledges the shell command is hard to mock, so behavior is only smoke-tested.
- `tests/scanners/test_apigateway_scanner.py:9` – Imports `MagicMock`, `patch`, and `AsyncMock` for API Gateway scanner tests.
- `tests/scanners/test_cloudfront_scanner.py:9` – Same mocking imports for CloudFront scanner coverage.
- `tests/scanners/test_container_scanner.py:9` – Scanner tests rely on `MagicMock`, `patch`, `AsyncMock`.
- `tests/scanners/test_cross_account.py:10` – Imports `MagicMock` and `patch` to emulate cross-account interactions.
- `tests/scanners/test_lambda_scanner.py:9` – Lambda scanner tests import common mocking helpers.
- `tests/scanners/test_multi_account.py:10` – Uses `MagicMock`, `patch`, `AsyncMock`.
- `tests/scanners/test_secrets_scanner.py:10` – Secrets scanner tests mock AWS interfaces.
- `tests/services/test_aws_connection.py:82` – Docstring describes stubbed boto3 factory fixtures.
- `tests/services/test_trial.py:622` – Imports `MagicMock` from `unittest.mock`.
- `tests/unit/alerting/test_sns_handler.py:5` – Imports `AsyncMock` and `MagicMock` to fake SNS clients.
- `tests/unit/test_aws_scanners.py:4` – Docstring clarifies the suite verifies logic without mocking AWS services.
- `tests/unit/test_cost_scanner.py:4` – Similar “without mocking” statement for cost scanner logic.
- `tests/unit/test_dependencies.py:4` – Imports `AsyncMock`, `MagicMock` for dependency resolver tests.
- `tests/unit/test_health.py:7` – Imports `AsyncMock`, `MagicMock`, `patch` for runtime health checks.
- `tests/unit/test_issue_23_container_packaging.py:4` – Notes the Dockerfile tests run without mocking tooling.
- `tests/unit/test_operations_scanner.py:4` – Declares scanner logic verification without mocks.
- `tests/unit/test_performance_scanner.py:4` – Same “no mocks” docstring for performance scanners.
- `tests/unit/test_reliability_scanner.py:4` – Reliability scanner suite avoids mocking AWS services.
- `tests/unit/test_secrets.py:6` – Imports `MagicMock` and `patch` for secrets utilities.
- `tests/unit/test_security_service.py:6` – Notes IB-service dependent tests use stub implementations instead of mocks.
- `tests/unit/test_ss_context_sync.py:49` – Defines a `mock_service` helper fixture.
- `tests/unit/test_ss_entity_migrator.py:114` – Docstring clarifies the migrator uses a mock IB service.
- `tests/unit/test_ss_hybrid.py:13` – Provides a minimal mock of the IB service for hybrid tests.
- `tests/unit/test_ss_relationship_migrator.py:106` – Describes creating migrators with mocked services and entity mappings.
- `tests/unit/test_ss_validator.py:65` – Fixture called `mock_ss_kg` supplies a mocked knowledge graph.

These references can guide deeper code reviews (e.g., auditing each suite for mocking best practices or identifying where real dependencies are intentionally used). Let me know if the inventory should include non-code assets or if you need richer metadata (owners, test categories, etc.).
