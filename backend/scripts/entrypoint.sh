#!/bin/bash
set -e

# 运行数据库迁移 (Alembic)
echo "Running database migrations..."
# 确保在 /app 目录下执行，这样才能找到 alembic.ini 和 migrations/
alembic upgrade head

# 启动 Gunicorn + Uvicorn
echo "Starting backend server..."
exec gunicorn -k uvicorn.workers.UvicornWorker \
     --bind 0.0.0.0:8000 \
     --workers ${WEB_CONCURRENCY:-2} \
     --timeout ${GUNICORN_TIMEOUT:-120} \
     app.main:app
