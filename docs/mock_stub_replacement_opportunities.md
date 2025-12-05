# Mock/Stub Replacement Opportunities

Follow-up analysis on top of `docs/mock_stub_usage_inventory.md` to spot tests where mocks are replaceable with real data or system interactions. Each entry references the relevant source file, describes the current mock/stub usage, and suggests how to remove it using fixtures or infrastructure already present in the repo.

## Ready with Existing Fixtures
- `tests/services/test_trial.py:619-627` – only `test_service_initialization` relies on `MagicMock` for a session. The module already provides `trial_service`/`db_session` fixtures, so this test can instantiate `TrialService(db_session)` and assert it shares the dependency, eliminating the mock entirely.
- `tests/unit/test_dependencies.py:13-54` – `get_ib_client` tests fabricate `MagicMock` requests. Switching to a real `fastapi.Request` created from `FastAPI()`/`TestClient` (or Starlette `Request(scope, receive)`) lets the test exercise the real request object and `app.state` without mocks.
- `tests/api/test_findings_api.py:1-26` – the API smoke test currently expects a 401 because auth is “mocked or bypassed.” The project already has real auth fixtures (`tests/api/test_auth_endpoints.py:1-120` defines `registered_user`, `auth_tokens`, `auth_headers`). Moving those fixtures into a shared conftest and using them here would allow authenticated calls that hit the real FastAPI router with seeded Postgres data.

## Needs LocalStack or External Emulators
- `tests/services/test_aws_connection.py:1-160` now uses the shared LocalStack/real AWS detection to provision boto3 sessions; no stubs remain.
- Scanner suites (`tests/scanners/test_container_scanner.py:1-80`, `tests/scanners/test_lambda_scanner.py:1-60`, `tests/scanners/test_apigateway_scanner.py:1-60`, `tests/scanners/test_cloudfront_scanner.py:1-60`, `tests/scanners/test_secrets_scanner.py:1-40`, and `tests/scanners/test_multi_account.py:1-90`) now draw their `boto_session` directly from `tests/scanners/conftest.py`, so rule/metadata verification runs against the same session plumbing used in production environments.
- `tests/scanners/test_cross_account.py` still relies on lightweight stand-ins for STS because LocalStack lacks cross-account IAM role support; refactoring this suite would require either multi-account AWS credentials or custom infrastructure to stand up trust relationships.

## Smart-Scaffold Suites (Swap in Real In-Memory Implementations)
- `tests/unit/test_ss_entity_migrator.py:260-404` defines `MockIBService` solely to track created entities. `cloud_optimizer/integrations/smart_scaffold/runtime.py:47-140` already exports `LocalIBService`, which persists entities/relationships in-memory. Using that class (optionally wrapped to inject failures) would remove the bespoke mock.
- `tests/unit/test_ss_relationship_migrator.py:107-420` mirrors the above for relationships. Again, `LocalIBService.create_relationship` and `.query_relationships` can provide the needed behavior without the custom `MockRelIBService`.
- `tests/unit/test_ss_context_sync.py:305-352` uses `MockContextIBService` for success-path tests even though `LocalIBService` provides `create_entity`, `create_relationship`, and `query_entities`. Only the failure-injection case would still need a small wrapper.
- `tests/unit/test_ss_hybrid.py:13-74` introduces `MockIBService`/`MockSSKG` for dual-write tests. Pairing `LocalIBService` with `StaticSSKnowledgeGraph` (see `runtime.py:47-205`) would ensure the adapter is talking to the same implementations used elsewhere in the migration tooling.
- `tests/unit/test_ss_validator.py:63-210` creates mock knowledge-graph and IB services to feed `MigrationValidator`. Those mocks can be replaced with `StaticSSKnowledgeGraph` instances initialized from sample data and `LocalIBService` (which exposes `query_entities`, `query_relationships`, `get_entity_by_id`, and `search_entities`).

Implementing the above changes would concentrate mocking to only the scenarios that truly require simulated failures or unsupported third-party APIs, giving deeper confidence in scanner, service, and Smart-Scaffold behavior.
