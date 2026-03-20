#!/usr/bin/env python3
"""Compatibility wrapper. Use scripts/db/add_portfolio_index.py."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parent / "db" / "add_portfolio_index.py"), run_name="__main__")
