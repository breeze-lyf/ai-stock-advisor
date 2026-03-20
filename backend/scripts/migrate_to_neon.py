#!/usr/bin/env python3
"""Compatibility wrapper. Use scripts/db/migrate_to_neon.py."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parent / "db" / "migrate_to_neon.py"), run_name="__main__")
