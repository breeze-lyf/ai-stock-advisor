FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    python3-dev \
    libpq-dev \
    gcc \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 暴露端口
# 暴露业务端口
EXPOSE 8000

# 小内存机器默认值：1 个 worker，优先保证稳定性；可通过 WEB_CONCURRENCY 覆盖
ENV PYTHONPATH=/app
ENV WEB_CONCURRENCY=1
ENV GUNICORN_TIMEOUT=120

# 数据库自动迁移集成
RUN chmod +x /app/scripts/entrypoint.sh
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
