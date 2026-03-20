#!/usr/bin/env python3
"""Compatibility wrapper. Use scripts/data/verify_news_persistence.py."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parent / "data" / "verify_news_persistence.py"), run_name="__main__")
