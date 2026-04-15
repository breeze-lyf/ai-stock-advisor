#!/bin/bash
# Kill all processes holding common development ports

set -euo pipefail

PORTS="${@:-3000 8000}"

echo "Killing processes on ports: $PORTS"

for port in $PORTS; do
    pids=$(lsof -ti:$port 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo "Port $port: Killing PIDs $pids"
        echo "$pids" | xargs kill -9 2>/dev/null || true
    else
        echo "Port $port: No processes found"
    fi
done

echo "Port cleanup complete."
