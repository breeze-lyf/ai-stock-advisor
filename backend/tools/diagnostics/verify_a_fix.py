#!/usr/bin/env python3
"""Compatibility wrapper. Use backend/scripts/dev/diagnostics counterpart."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parents[2] / "scripts" / "dev" / "diagnostics" / Path(__file__).name), run_name="__main__")
