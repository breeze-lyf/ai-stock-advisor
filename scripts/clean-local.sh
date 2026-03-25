#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "Cleaning local caches and generated artifacts..."

rm -rf "$ROOT_DIR/.pytest_cache"
rm -rf "$ROOT_DIR/backend/.pytest_cache"
rm -rf "$ROOT_DIR/frontend/.next"
rm -rf "$ROOT_DIR/mobile/dist"
rm -rf "$ROOT_DIR/backend/runtime-logs"
rm -rf "$ROOT_DIR/backend/.local/runtime-logs"

find "$ROOT_DIR" -maxdepth 1 -type f \
  \( -name "*test_results*.log" -o -name "final_*results*.log" -o -name "app.log" -o -name "ai_calls.log" \) \
  -delete

find "$ROOT_DIR/backend" -maxdepth 1 -type f \
  \( -name "*.log" -o -name "*.db" \) \
  -delete

mkdir -p "$ROOT_DIR/backend/.local/runtime-logs"

echo "Local cleanup complete."
