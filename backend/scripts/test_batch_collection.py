#!/usr/bin/env python3
"""Compatibility wrapper. Use scripts/dev/test_batch_collection.py."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parent / "dev" / "test_batch_collection.py"), run_name="__main__")
