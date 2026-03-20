#!/usr/bin/env python3
"""Compatibility wrapper. Use scripts/dev/test_data_fetching_perf.py."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parent / "dev" / "test_data_fetching_perf.py"), run_name="__main__")
