from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

RUN_PROVIDER_NETWORK_TESTS = os.getenv("RUN_PROVIDER_NETWORK_TESTS", "").lower() in {
    "1",
    "true",
    "yes",
    "on",
}


def pytest_ignore_collect(collection_path, config):
    """Skip provider tests by default to avoid flaky network-dependent CI runs."""
    path = Path(str(collection_path))
    if "tests" in path.parts and "provider" in path.parts and not RUN_PROVIDER_NETWORK_TESTS:
        return True
    return False


def pytest_collection_modifyitems(config, items):
    """Apply directory-based markers automatically for consistent test layering."""
    for item in items:
        parts = Path(str(item.fspath)).parts
        if "tests" not in parts:
            continue
        if "unit" in parts:
            item.add_marker("unit")
        elif "integration" in parts:
            item.add_marker("integration")
        elif "provider" in parts:
            item.add_marker("provider")
