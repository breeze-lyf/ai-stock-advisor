#!/usr/bin/env python3
"""Compatibility wrapper. Use scripts/db/check_db_v3.py."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parent / "db" / "check_db_v3.py"), run_name="__main__")
