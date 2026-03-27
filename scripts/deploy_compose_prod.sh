#!/usr/bin/env bash
set -euo pipefail

DEPLOY_STAGE="preflight"

dump_compose_diagnostics() {
  if [ "$DEPLOY_STAGE" = "preflight" ]; then
    echo "Deployment failed before containers were updated."
    return
  fi
  echo "Deployment failed. Collecting compose diagnostics..."
  ${COMPOSE_CMD} -f docker-compose.prod.yml ps || true
  docker inspect stock_backend --format '{{json .State.Health}}' 2>/dev/null || true
  ${COMPOSE_CMD} -f docker-compose.prod.yml logs --tail=200 backend || true
  ${COMPOSE_CMD} -f docker-compose.prod.yml logs --tail=80 frontend || true
}

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

trap dump_compose_diagnostics ERR

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
echo "Cleaning up disk space (proactive prune)..."
docker system prune -af --volumes || true

echo "Pulling images..."
${COMPOSE_CMD} -f docker-compose.prod.yml pull

BACKEND_IMAGE="${ACR_REGISTRY}/ai-stock-advisor/stock-backend:${APP_IMAGE_TAG:-latest}"

echo "Running database preflight check with ${BACKEND_IMAGE}..."
docker run --rm \
  --env-file ./backend/.env \
  --add-host host.docker.internal:host-gateway \
  --workdir /app \
  -e PYTHONPATH=/app \
  --entrypoint python \
  "${BACKEND_IMAGE}" \
  /app/scripts/check_database_connectivity.py

echo "Starting containers..."
DEPLOY_STAGE="compose-up"
${COMPOSE_CMD} -f docker-compose.prod.yml up -d

echo "Deployment completed"
${COMPOSE_CMD} -f docker-compose.prod.yml ps
