# AI Smart Investment Advisor

AI 投资分析与组合辅助系统。当前仓库包含 Web 前端、FastAPI 后端、Taro 移动端，以及少量部署与运维辅助目录。

## 当前文档入口

- 主文档索引：`docs/README.md`
- 产品基线：`docs/01_Product_Requirements_Document.md`
- 开发执行指南：`docs/02_Developer_SOP_and_Guide.md`
- 数据库设计：`docs/04_Database_Design.md`
- 当前功能状态矩阵：`docs/05_Current_Feature_Status_Matrix.md`

根目录 `README` 只保留快速上手和目录导航。阶段性总结、升级记录、一次性规划文档已归档到 `docs/archive/2026-04/`。

## 当前仓库形态

- Web：Next.js 16 + React 19 + TypeScript
- Backend：FastAPI + SQLAlchemy Async + Alembic
- Mobile：Taro 4 + React 18
- Database：PostgreSQL / Neon
- Cache / Queue 辅助：Redis
- AI Provider：系统内置模型 + 用户 BYOK

## 快速启动

### 本地开发

```bash
./scripts/start.sh dev
```

默认行为：

- 前端运行在 `3000`
- 后端运行在 `8000`
- 数据库连接取自 `backend/.env`
- 后端启动时会拉起系统模型注册与后台调度
- 运行日志写入 `backend/.local/runtime-logs/`

手动启动：

```bash
cd backend
../.venv/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

```bash
cd frontend
npm run dev -- -p 3000
```

### 容器模式

```bash
./scripts/start.sh docker
```

或：

```bash
docker compose up --build -d
```

### 生产推荐

建议使用 GitHub Actions 构建镜像，服务器仅执行拉镜像和编排启动：

- 工作流：`.github/workflows/deploy.yml`
- 编排文件：`docker-compose.prod.yml`
- 部署脚本：`scripts/deploy_compose_prod.sh`

## 目录导航

- `frontend/`: Web 前端
- `backend/`: FastAPI 后端、迁移、脚本、测试
- `mobile/`: Taro 移动端
- `cloudflare-worker/`: 大陆网络场景下的 Yahoo Finance 代理
- `docs/`: 产品、研发、部署、数据库、状态矩阵与归档文档
- `scripts/`: 项目级启动和部署脚本
- `monitoring/`: 监控配置
- `.local/`: 本地私有资产与临时产物，不纳入版本控制

## 开发约定

- 文档优先级：代码实际行为 > `docs/05` 状态矩阵 > `docs/02` SOP > `docs/01` PRD
- 接口结构变更后，必须同步更新 OpenAPI、前端类型和相关文档
- 阶段性总结不要继续堆在根目录，统一放到 `docs/archive/`

## 子模块说明

- Web 前端说明：`frontend/README.md`
- Backend 脚本说明：`backend/scripts/README.md`
- Cloudflare Worker 说明：`cloudflare-worker/README.md`
- Mobile 环境搭建：`mobile/RN_SETUP.md`
