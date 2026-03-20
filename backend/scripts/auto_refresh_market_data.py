#!/usr/bin/env python3
"""Compatibility wrapper. Use scripts/data/auto_refresh_market_data.py."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parent / "data" / "auto_refresh_market_data.py"), run_name="__main__")
