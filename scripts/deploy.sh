#!/bin/bash
set -e  # 任何命令失败就立即停止

# AI 智能投顾系统 - 生产环境部署脚本

echo "🚀 开始部署 AI Smart Investment Advisor..."

# 1. 检查环境变量文件
if [ ! -f "backend/.env" ]; then
    echo "❌ 错误: backend/.env 文件不存在，请参考 .env.example 创建。"
    exit 1
fi

# 2. 拉取最新代码 (如果你使用 git)
# git pull origin main

# 3. 停止并移除旧容器
echo "停止旧服务..."
docker-compose down

# 4. 构建并启动服务
echo "构建并启动服务..."
# --build 强制重新构建镜像
if ! docker-compose up -d --build; then
    echo "❌ 部署失败！请查看上面的错误信息。"
    exit 1
fi

# 5. 等待服务启动
echo "等待服务启动..."
sleep 5

# 6. 检查后端是否运行
if ! docker-compose ps | grep -q "stock_backend.*Up"; then
    echo "❌ 后端服务未成功启动！"
    echo "查看日志: docker-compose logs backend"
    exit 1
fi

# 7. 执行数据库迁移
echo "执行数据库迁移..."
docker-compose exec backend alembic upgrade head

# 8. 清理无用镜像
echo "清理无用镜像..."
docker image prune -f

echo "✅ 部署完成!"
echo "后端地址: http://localhost:8000"
echo "前端地址: http://localhost:3000"
echo "查看日志命令: docker-compose logs -f"
