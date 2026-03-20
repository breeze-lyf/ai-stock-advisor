#!/usr/bin/env python3
"""Compatibility wrapper. Use scripts/db/migrate_llm_data.py."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parent / "db" / "migrate_llm_data.py"), run_name="__main__")
