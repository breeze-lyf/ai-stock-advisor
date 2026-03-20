#!/usr/bin/env python3
"""Compatibility wrapper. Use scripts/data/data_collector.py."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parent / "data" / "data_collector.py"), run_name="__main__")
