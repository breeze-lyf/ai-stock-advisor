#!/usr/bin/env python3
"""Compatibility wrapper. Use scripts/db/seed_stocks.py."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parent / "db" / "seed_stocks.py"), run_name="__main__")
