"""E2E test configuration.

E2E tests require a running application server at localhost:8000.
They are skipped by default and only run when explicitly invoked
with the --e2e flag or by running tests/e2e/ directly.

Playwright's sync_api manages its own event loop which conflicts with
pytest-asyncio's loop used by unit/integration tests. Isolating e2e
tests behind a marker prevents event loop contamination.
"""

import pytest


def pytest_collection_modifyitems(config, items):
    """Skip e2e tests unless --e2e flag is provided or tests/e2e/ is targeted."""
    # If user explicitly runs tests/e2e/, don't skip
    if any("e2e" in str(arg) for arg in config.args):
        return

    skip_e2e = pytest.mark.skip(
        reason="E2E tests require --e2e flag and a running server at localhost:8000"
    )
    for item in items:
        if "e2e" in str(item.fspath):
            item.add_marker(skip_e2e)
