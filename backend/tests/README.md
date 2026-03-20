# Backend Tests

Tests are organized by scope:

- `tests/unit/`: pure logic/unit tests with minimal external dependencies
- `tests/integration/`: API/DB integration and end-to-end smoke tests
- `tests/provider/`: market/provider connectivity and provider-specific behavior tests

Conventions:

- File names: `test_<subject>.py`
- Put provider-focused tests only in `tests/provider/`
- Keep manual/diagnostic tests explicit in naming (e.g. `*_proxy`, `*_direct`)

Quick examples:

- Run unit tests: `pytest backend/tests/unit -q`
- Run integration tests: `pytest backend/tests/integration -q`
- Run provider tests (network required): `RUN_PROVIDER_NETWORK_TESTS=1 pytest backend/tests/provider -q`

Marker policy:

- Markers are assigned automatically by directory:
- `tests/unit/**` -> `@pytest.mark.unit`
- `tests/integration/**` -> `@pytest.mark.integration`
- `tests/provider/**` -> `@pytest.mark.provider`

CI stability policy:

- Provider tests are ignored by default because they depend on external APIs/network/proxy state.
- To opt in locally or in dedicated jobs, set `RUN_PROVIDER_NETWORK_TESTS=1`.
