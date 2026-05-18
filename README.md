# AI Smart Investment Advisor

AI Smart Investment Advisor 是一个面向个人投资者和早期小团队的 AI 投资分析与组合辅助系统。它把持仓、行情、宏观、新闻、通知、模拟交易和 AI 分析放在同一个产品链路里，目标是帮助用户形成更可追踪、更可复盘的投资判断。

> 本项目提供研究和分析辅助，不提供投资承诺，也不应被当作自动实盘交易系统。

## 当前定位

- 核心问题：把分散的市场信息和个人持仓整理成可行动、可解释、可复盘的分析辅助。
- 当前阶段：优先建设 Web 产品、FastAPI 后端、AI Provider/BYOK、多源行情、通知和后台调度能力。
- 架构取舍：未来 6 个月按早期产品规模设计，采用清晰模块化单体，不提前引入 Kubernetes、大规模微服务拆分或复杂队列集群。
- 交付口径：代码实际行为优先；文档用于同步产品边界、研发规则、数据库设计、功能状态和 AI 协作决策。

## 技术栈

| 模块                 | 技术                                                       |
| -------------------- | ---------------------------------------------------------- |
| Web Frontend         | Next.js 16, React 19, TypeScript, Tailwind CSS 4, Radix UI |
| Backend              | FastAPI, SQLAlchemy Async, Alembic, Pydantic               |
| Database             | PostgreSQL / Neon                                          |
| Cache / Coordination | Redis                                                      |
| AI Provider          | 系统内置模型 + 用户 BYOK，多 Provider 路由与容灾           |
| Market Data          | A/H/US 行情、多源 Provider、缓存与后台刷新                 |
| Deployment           | Docker, GitHub Actions, Aliyun ACR, server pull mode       |

## 已落地能力

当前功能状态以 `docs/05_Current_Feature_Status_Matrix.md` 为准。高层概览如下：

- 已完成：注册登录、用户设置、持仓管理、组合汇总、股票搜索、A/H/US 行情、单股 AI 诊断、组合 AI 分析、宏观雷达、通知中心、飞书警报、AI 模型管理、模拟交易基础、监控诊断接口、自动部署链路。
- 部分完成：StockCapsule、增强分析、财经日历、选股器、Truth Tracker 可视化、FREE/PRO 分层。
- 骨架已入库：量化因子、回测引擎、自选分组、组合风险、订阅支付、Academy。

## 快速启动

### 统一启动

```bash
./scripts/start.sh dev
```

默认行为：

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- Backend env: `backend/.env`
- Runtime logs: `backend/.local/runtime-logs/`
- 后端启动时会执行代理环境标准化、系统模型注册和后台调度初始化。

### 手动启动

Backend:

```bash
cd backend
../.venv/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm run dev -- -p 3000
```

### Docker 启动

```bash
./scripts/start.sh docker
```

或：

```bash
docker compose up --build -d
```

## 常用命令

安装依赖：

```bash
npm run install-all
```

前端检查：

```bash
cd frontend
npm run lint
npm run build
npm run generate-types
```

后端测试：

```bash
pytest backend/tests/unit -q
pytest backend/tests/integration -q
RUN_PROVIDER_NETWORK_TESTS=1 pytest backend/tests/provider -q
```

数据库迁移：

```bash
cd backend
alembic revision --autogenerate -m "your_migration_name"
alembic upgrade head
```

## 环境变量 

本地开发主要依赖 `backend/.env` 和前端公开环境变量。

关键项：

- `DATABASE_URL`: PostgreSQL / Neon 连接。
- `SECRET_KEY`: 后端鉴权密钥。
- `REDIS_URL`: Redis 连接，影响缓存、通知去重和调度锁。
- AI Provider keys: 系统内置模型供应商密钥。
- `NEXT_PUBLIC_API_URL`: 前端访问后端 API 的地址。

敏感信息不要提交到仓库，不要写入日志，不要在截图或最终总结中展示。

## 架构入口

```text
frontend/
  app/                  Next.js App Router 页面编排
  components/           业务组件和 UI primitives
  features/             领域 API、hooks、状态逻辑
  shared/api/client     统一 API client
  types/schema.d.ts     OpenAPI 生成类型

backend/
  app/api/v1/endpoints/ FastAPI routers
  app/application/      用例编排
  app/services/         业务服务、AI 路由、行情、调度、通知
  app/models/           SQLAlchemy ORM
  app/schemas/          Pydantic contracts
  migrations/           Alembic migrations
  tests/                unit / integration / provider tests

docs/                   长期基线文档
scripts/                启动、部署和运维脚本
image/                  设计、蓝图和产品素材
```

## 开发规则

- 后端 router 保持薄层，复杂业务放到 `application/**` 或 `services/**`。
- 前端页面层只做路由和编排，接口调用优先放到 `frontend/features/**/api.ts` 或共享 API client。
- 接口结构变化必须同步：后端 schema、OpenAPI、前端生成类型、API wrapper、UI 和相关文档。
- 数据库结构变化必须走 Alembic migration，不手改线上表结构。
- AI Provider/BYOK 相关逻辑必须走 `ai_service.py`、`model_resolver.py`、`provider_router.py` 既有链路。
- Provider/network 测试依赖外部网络和代理状态，默认不作为稳定 CI 前置，相关任务中显式运行。

## AI 协作记忆

本仓库同时维护面向 AI 编程助手的长期上下文：

- `AGENTS.md`: Codex 项目说明书，记录默认语言、安全约束、架构契约、命令、分层规则和交付要求。
- `CLAUDE.md`: 如果存在，用于 Claude Code 读取项目约定。
- `docs/08_Agent_Decision_Log.md`: 记录 AI 协作中产生的长期产品判断、现实假设和架构权衡。

会影响未来开发判断的产品、架构、依赖、安全或测试策略决定，应追加到 `docs/08_Agent_Decision_Log.md`，不要把根目录 README 变成会话流水账。

## 文档入口

- `docs/README.md`: 文档索引和维护规则。
- `docs/01_Product_Requirements_Document.md`: 产品目标、范围边界、阶段规划。
- `docs/02_Developer_SOP_and_Guide.md`: 开发执行规范、分层约束、交付规则。
- `docs/03_Mainland_Deployment_Guide.md`: 大陆环境部署和网络适配。
- `docs/04_Database_Design.md`: 数据库结构和设计意图。
- `docs/05_Current_Feature_Status_Matrix.md`: 功能状态、测试优先级和最小回归集。
- `docs/06_AI_Analysis_Implementation_Guide.md`: AI 增强分析架构与实现。
- `docs/07_Agent_Architecture_Design.md`: Agent 任务拆解和输出规范。
- `docs/08_Agent_Decision_Log.md`: AI 协作决策日志。

## 部署

生产推荐使用“GitHub Actions 构建镜像，服务器只拉镜像和编排启动”的模式，适合低配服务器。

- Workflow: `.github/workflows/deploy.yml`
- Compose: `docker-compose.prod.yml`
- Deploy script: `scripts/deploy_compose_prod.sh`
- Image registry: Aliyun ACR

部署相关 secrets 包括 ACR、SSH、服务器地址和前端公开 API 地址，均通过 GitHub Actions secrets 管理。

## 维护约定

- 根目录 README 只保留项目首页、快速启动、架构入口和协作规则。
- 长期基线写入 `docs/`。
- 阶段性总结、一次性方案和历史材料放到 `docs/archive/<yyyy-mm>/`。
- 文档优先级：代码实际行为 > `docs/05` 状态矩阵 > `docs/02` SOP > `docs/01` PRD。
- 如果文档与代码不一致，在相关变更中同步修正文档。
