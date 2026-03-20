#!/usr/bin/env python3
"""Compatibility wrapper. Use scripts/db/reset_password.py."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parent / "db" / "reset_password.py"), run_name="__main__")
