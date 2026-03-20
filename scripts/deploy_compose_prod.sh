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

echo "Using compose command: ${COMPOSE_CMD}"
echo "Pulling images..."
${COMPOSE_CMD} -f docker-compose.prod.yml pull

echo "Starting containers..."
${COMPOSE_CMD} -f docker-compose.prod.yml up -d

echo "Running migrations..."
${COMPOSE_CMD} -f docker-compose.prod.yml exec -T backend alembic upgrade head

echo "Deployment completed"
${COMPOSE_CMD} -f docker-compose.prod.yml ps
