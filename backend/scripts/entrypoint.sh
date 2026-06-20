#!/bin/bash
set -e

ALEMBIC_LOG=$(mktemp)
cleanup() {
    rm -f "$ALEMBIC_LOG"
}
trap cleanup EXIT

# 运行数据库迁移 (Alembic)
echo "PHASE: Checking database connectivity..."

# 提取并脱敏打印 DATABASE_URL (仅用于诊断，生产环境请根据安全需求调整)
# 注意：这里假设 URL 格式为 postgresql+asyncpg://user:pass@host:port/db
if [[ "$DATABASE_URL" == *"postgresql"* ]]; then
    CLEAN_URL=$(echo $DATABASE_URL | sed -e 's/\/\/.*@/\/\/****:****@/g')
    echo "Using DATABASE_URL: $CLEAN_URL"
fi

echo "Running database migrations..."
# 尝试运行迁移，如果失败则输出详细错误并退出
if ! alembic upgrade head 2>&1 | tee "$ALEMBIC_LOG"; then
    if grep -qi "compute time quota" "$ALEMBIC_LOG"; then
        echo "ERROR: Neon compute time quota exceeded. Resume or upgrade the Neon project before redeploying."
    fi
    echo "ERROR: Database migration failed!"
    exit 1
fi

# 启动 Gunicorn + Uvicorn
echo "Starting backend server..."
exec gunicorn -k uvicorn.workers.UvicornWorker \
     --bind 0.0.0.0:8000 \
     --workers ${WEB_CONCURRENCY:-2} \
     --timeout ${GUNICORN_TIMEOUT:-120} \
     app.main:app
