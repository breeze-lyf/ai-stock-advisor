#!/usr/bin/env python3
"""Compatibility wrapper. Use backend/scripts/db/sync_db.py."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parent / "scripts" / "db" / "sync_db.py"), run_name="__main__")
