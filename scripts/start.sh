#!/bin/bash

set -euo pipefail

MODE="${1:-dev}"
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
DEV_HOST="${DEV_HOST:-127.0.0.1}"

port_listener() {
    local port="$1"
    lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null | tail -n +2 || true
}

ensure_port_free() {
    local port="$1"
    local service_name="$2"
    local listener

    listener="$(port_listener "$port")"
    if [ -n "$listener" ]; then
        echo "Error: port $port is already in use, cannot start $service_name."
        echo "$listener"
        echo "Stop the existing process or run with a different port:"
        echo "  BACKEND_PORT=... FRONTEND_PORT=... ./scripts/start.sh dev"
        exit 1
    fi
}

install_backend_deps() {
    local pip_exec="$1"
    local stamp_file="$ROOT_DIR/backend/.deps.stamp"

    if [ ! -f "$stamp_file" ] || [ "$ROOT_DIR/backend/requirements.txt" -nt "$stamp_file" ]; then
        echo "Installing backend dependencies..."
        "$pip_exec" install -r "$ROOT_DIR/backend/requirements.txt" >/dev/null
        touch "$stamp_file"
    fi
}

install_frontend_deps() {
    local stamp_file="$ROOT_DIR/frontend/node_modules/.deps.stamp"

    if [ ! -d "$ROOT_DIR/frontend/node_modules" ] || \
       [ ! -f "$stamp_file" ] || \
       [ "$ROOT_DIR/frontend/package.json" -nt "$stamp_file" ] || \
       [ "$ROOT_DIR/frontend/package-lock.json" -nt "$stamp_file" ]; then
        echo "Installing frontend dependencies..."
        cd "$ROOT_DIR/frontend"
        npm install >/dev/null
        mkdir -p "$ROOT_DIR/frontend/node_modules"
        touch "$stamp_file"
    fi
}

print_usage() {
    cat <<'EOF'
Usage:
  ./scripts/start.sh dev       Start the local development stack
  ./scripts/start.sh docker    Start the containerized stack with Docker Compose

Notes:
  - `dev` is for local development only.
  - `docker` is the deployment-style startup path for this repository.
EOF
}

start_dev() {
    trap "trap - SIGTERM && kill -- -$$" SIGINT SIGTERM EXIT

    echo "Starting local development stack..."

    if ! command -v npm >/dev/null 2>&1; then
        echo "Error: npm is not installed"
        exit 1
    fi

    if ! command -v python3 >/dev/null 2>&1; then
        echo "Error: python3 is not installed"
        exit 1
    fi

    local python_exec="$ROOT_DIR/.venv/bin/python3"
    local pip_exec="$ROOT_DIR/.venv/bin/pip3"

    if [ ! -x "$python_exec" ]; then
        python_exec="python3"
    fi
    if [ ! -x "$pip_exec" ]; then
        pip_exec="pip3"
    fi

    ensure_port_free "$BACKEND_PORT" "backend"
    ensure_port_free "$FRONTEND_PORT" "frontend"

    echo "Starting backend on http://$DEV_HOST:$BACKEND_PORT ..."
    cd "$ROOT_DIR/backend"
    install_backend_deps "$pip_exec"
    WATCHFILES_FORCE_POLLING=true \
    "$python_exec" -m uvicorn app.main:app --reload --host "$DEV_HOST" --port "$BACKEND_PORT" &

    echo "Starting market auto-refresh worker..."
    "$python_exec" scripts/auto_refresh_market_data.py > auto_refresh.log 2>&1 &

    echo "Starting frontend on http://$DEV_HOST:$FRONTEND_PORT ..."
    cd "$ROOT_DIR/frontend"
    rm -rf .next/dev/lock
    install_frontend_deps
    npm run dev -- --hostname "$DEV_HOST" -p "$FRONTEND_PORT" &

    cd "$ROOT_DIR"
    echo "Development stack is running."
    echo "Frontend: http://$DEV_HOST:$FRONTEND_PORT"
    echo "Backend:  http://$DEV_HOST:$BACKEND_PORT/docs"
    wait
}

start_docker() {
    cd "$ROOT_DIR"

    if ! command -v docker >/dev/null 2>&1; then
        echo "Error: docker is not installed"
        exit 1
    fi

    echo "Starting containerized stack with Docker Compose..."
    docker compose up --build -d
    echo "Frontend: http://localhost:3000"
    echo "Backend:  http://localhost:8000/docs"
}

case "$MODE" in
    dev)
        start_dev
        ;;
    docker)
        start_docker
        ;;
    -h|--help|help)
        print_usage
        ;;
    *)
        echo "Unknown mode: $MODE"
        print_usage
        exit 1
        ;;
esac
