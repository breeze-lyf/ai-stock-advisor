#!/usr/bin/env python3
"""Compatibility wrapper. Use scripts/data/benchmark_news.py."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parent / "data" / "benchmark_news.py"), run_name="__main__")
