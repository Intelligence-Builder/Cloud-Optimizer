# Integration Test Gap Analysis

Date: 2025-11-30

This document consolidates the current state of Cloud Optimizer's integration
tests and enumerates the remaining gaps required for end-to-end coverage using
*real services* (PostgreSQL, Memgraph, LocalStack, FastAPI) without mocks.

## Existing Coverage

| Area | Test Files | Real Systems Exercised | Notes |
|------|------------|------------------------|-------|
| Graph parity & traversal | `test_epic1_platform.py`, `test_epic1_performance.py` | PostgresCTE backend, Memgraph | 100-node parity suite, traversal and performance assertions |
| Cost/Reliability/Performance scanning | `test_epic4_scanners.py` | LocalStack (IAM/EC2/S3), AWS client wrappers | Validates findings transformation and LocalStack responses |
| Application boot/API smoke | `test_epic3_app.py`, `test_security_api.py` | FastAPI app, real dependency injection | Exercises `/health`, `/api/v1/security/*` flows |
| Smart-Scaffold service layer | `test_epic5_ss_integration.py` | Postgres-backed `RealPostgresIBService`, Memgraph adapter substitute | Validates entity/relationship migrators, validators, cutover service |

These suites rely exclusively on the dockerised infrastructure defined in
`docker/docker-compose.test.yml` and therefore satisfy the "no mocks" standard.

## Identified Gaps

1. **Smart-Scaffold CLI/Runtime Workflow**
   - *Issue*: Tests cover individual migrator classes but never execute the
     shipping CLI entrypoints (`scripts/migrate_ss_entities.py`,
     `scripts/migrate_ss_to_ib.py`, `scripts/run_parallel_validator.py`).
   - *Impact*: We risk regressions in argument parsing, validation printing, and
     runtime fallback logic (memory/sd/http) because only unit tests touched the
     helpers.
   - *Action*: Added `tests/integration/test_ss_cli_workflow.py` which
     synthesises sample Smart-Scaffold exports, invokes `run_full_migration_cli`
     via its public wrapper, captures the JSON validation summary, and asserts
     that the generated mapping contains every exported entity. This ensures the
     CLI path (async runners, mapping persistence, validator invocation) works on
     real data without mocks.

2. **CLI Cleanup Workflow**
   - *Issue*: The new cleanup command was only unit-tested. Integration coverage
     was missing to confirm the command-line entrypoint deletes evidence files
     when pointed at an actual temp directory.
   - *Action*: The integration CLI test uses temporary directories and invokes
     `run_full_migration_cli` followed by `run_cleanup_cli` to ensure evidence
     cleanup works in practice (no mocking of filesystem calls).

3. **IB HTTP fallback coverage**
   - *Observation*: Runtime falls back to an httpx client when the IB SDK cannot
     authenticate. The integration CLI test intentionally hits this path (no SDK
     server) so every run asserts the HTTP fallback can migrate and validate
     sample entities.

4. **Parallel Validator evidence** *(Pending)*
   - *Gap*: We still need a deterministic integration test that demonstrates
     discrepancy logging when Smart-Scaffold and IB datasets diverge. This will
     require wiring the CLI to prime IB while loading a different dataset into
     `StaticSSKnowledgeGraph`. This is tracked for the next iteration once the
     validator supports distinct entity inputs for IB vs SS.

## Action Items

1. ✅ Add `test_ss_cli_workflow.py` to exercise `run_full_migration_cli` end-to-end
   with sample exports (memory backend, validation summary asserting success).
2. ✅ Ensure CLI cleanup helper works against real files by invoking
   `run_cleanup_cli` in the integration suite.
3. ⏳ Extend `run_parallel_validator_cli` to accept distinct SS/IB entity inputs
   so we can script a deterministic discrepancy test (future work).
4. ⏳ Monitor IB API delete semantics (currently soft-delete endpoint returns
   HTTP 500). Until the API implements entity removal, integration clean-up of IB
   data will continue to rely on `docker compose down -v` in the IB repo.
