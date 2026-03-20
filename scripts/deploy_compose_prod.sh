#!/usr/bin/env bash
set -euo pipefail

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required"
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD="docker-compose"
else
  echo "docker compose or docker-compose is required"
  exit 1
fi

if [ ! -f "./backend/.env" ]; then
  echo "missing ./backend/.env"
  exit 1
fi

if [ -z "${ACR_REGISTRY:-}" ]; then
  echo "ACR_REGISTRY is required"
  exit 1
fi

# 根据项目准则，清理可能残留的进程以释放端口
echo "Cleaning up possible port conflicts (8000 & 3000)..."
if command -v pm2 >/dev/null 2>&1; then
  pm2 stop all 2>/dev/null || true
  pm2 delete all 2>/dev/null || true
fi
fuser -k 8000/tcp 3000/tcp 2>/dev/null || true

echo "Using compose command: ${COMPOSE_CMD}"
echo "Pulling images..."
${COMPOSE_CMD} -f docker-compose.prod.yml pull

echo "Starting containers..."
${COMPOSE_CMD} -f docker-compose.prod.yml up -d

echo "Running migrations..."
${COMPOSE_CMD} -f docker-compose.prod.yml exec -T backend alembic upgrade head

echo "Deployment completed"
${COMPOSE_CMD} -f docker-compose.prod.yml ps
