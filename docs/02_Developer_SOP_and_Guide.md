# 02. 开发者 SOP 与代码指南 (Developer SOP & Guide)

**定位：** 本文档用于统一研发与测试的执行口径，确保“代码实现、运行方式、文档描述”三者一致。本文只描述当前仓库落地现状与可执行流程，不写远期设想。

---

## 1. 当前技术栈基线（2026-04）

### 1.1 Web 前端

- Next.js 16（App Router）
- React 19
- TypeScript 5
- Tailwind CSS 4 + Radix UI
- Axios 请求层 + OpenAPI 类型生成

### 1.2 后端

- FastAPI（Python 3.10+）
- SQLAlchemy 2.0（Async）+ Alembic
- Neon Postgres / PostgreSQL（主数据源）
- Redis（缓存、去重、通知辅助）
- FastAPI lifespan 拉起后台调度协程

### 1.3 移动端

- Taro 4.1 + React 18
- 与 Web 共用后端 API

---

## 2. 运行方式（统一口径）

### 2.1 本地开发模式

适用场景：日常功能开发、联调、排查问题。

启动命令：

```bash
./scripts/start.sh dev
```

说明：

- 前端默认在 3000 端口
- 后端默认在 8000 端口
- 数据库连接由 `backend/.env` 的 `DATABASE_URL` 决定
- 后端启动后会自动执行：代理环境标准化、系统模型注册、调度协程拉起

### 2.2 容器模式

适用场景：接近生产结构的预发布验证。

启动命令：

```bash
./scripts/start.sh docker
```

或：

```bash
docker compose up --build -d
```

### 2.3 生产推荐模式（低配服务器）

建议使用“GitHub 构建镜像 + 服务器只拉镜像”的方式，避免在 2G 机器上本地构建。

- 工作流：`.github/workflows/deploy.yml`
- 生产编排：`docker-compose.prod.yml`
- 部署脚本：`scripts/deploy_compose_prod.sh`

---

## 3. 分层与代码职责红线

### 3.1 前端分层

| 层级 | 目录示例 | 允许职责 | 禁止事项 |
|------|----------|----------|----------|
| 页面编排层 | `frontend/app/**` | 路由参数、页面级加载、子组件编排 | 在页面中堆积复杂业务计算 |
| 业务组件层 | `frontend/components/features/**` | 展示业务逻辑、消费结构化数据 | 跨域复制请求逻辑、随意改响应结构 |
| API/类型层 | `frontend/features/**/api.ts`、`frontend/types/schema.d.ts` | 请求封装、超时策略、错误映射 | 在组件里散落手写请求地址 |
| 原子 UI 层 | `frontend/components/ui/**` | 可复用基础 UI | 绑定具体业务状态 |

### 3.2 后端分层

| 层级 | 目录示例 | 允许职责 | 禁止事项 |
|------|----------|----------|----------|
| Router 层 | `backend/app/api/v1/endpoints/**` | 入参校验、调用服务、返回响应 | 写重业务逻辑或复杂 SQL |
| Service 层 | `backend/app/services/**` | 核心业务编排、外部服务调用、容错降级 | 直接承载 HTTP 协议细节 |
| Model/Schema 层 | `backend/app/models/**`、`backend/app/schemas/**` | 数据结构定义、输入输出契约 | 在模型层写流程逻辑 |
| Infra 层 | `backend/app/infrastructure/**` | Repository、持久化细节 | 越层调用路由或 UI 逻辑 |

---

## 4. 数据与迁移纪律

1. 所有结构变更必须通过 Alembic，不允许手改线上表结构。
2. 开发流程：改模型 -> 生成迁移 -> 本地验证 -> Neon 临时分支验证 -> 合并。
3. 数据库主连接一律走 `DATABASE_URL`，不得在代码里硬编码 SQLite 回退。

常用命令：

```bash
cd backend
alembic revision --autogenerate -m "your_migration_name"
alembic upgrade head
```

---

## 5. 新增字段/指标的标准链路

以新增行情字段为例，必须完整打通以下链路：

1. Provider 抓取：`backend/app/services/market_providers/**`
2. 持久化模型：`backend/app/models/**`
3. 业务组装：`backend/app/services/market_data*.py`
4. 响应 schema：`backend/app/schemas/**`
5. OpenAPI 重新生成：`backend/openapi.json`
6. 前端类型同步：`frontend/types/schema.d.ts`
7. 前端展示接线：`frontend/components/features/**`

任一层未更新，都视为“不完整交付”。

---

## 6. AI 能力开发约束

1. 默认系统模型按当前注册信息走 `qwen3.5-plus`，不要在业务代码写死临时模型名。
2. BYOK 配置必须走用户模型配置链路，不直接读取明文 Key 到日志。
3. AI 输出解析必须保持结构化字段兼容，关键字段变更需要同步前端展示组件。
4. 供应商错误必须区分可重试与不可重试（鉴权失败、模型不存在、超时）。

---

## 7. 稳定性与质量要求

### 7.1 前端

- 避免 `any`，优先使用 OpenAPI 派生类型
- 请求超时应在 API 层集中配置，不在组件层分散硬编码
- 鉴权失效路径统一由 API 客户端拦截器处理

### 7.2 后端

- 三方数据入库前必须做空值与异常值防御
- 异步任务必须可取消、可观测（日志可追踪）
- 对外错误信息避免泄露内部堆栈

---

## 8. 提交流程（研发/测试通用）

1. 开发前确认目标模块是否在当前基线内（见状态矩阵）。
2. 代码完成后自测核心链路，至少覆盖“成功路径 + 失败路径”。
3. 若涉及接口结构变化，必须同步更新 OpenAPI 与前端类型。
4. 更新相关文档：README、SOP、状态矩阵中对应项。
5. 提交说明需写清：改了什么、影响范围、如何验证。

---

## 9. 文档协同规则

- PRD 负责产品目标与阶段规划。
- README 负责仓库首页与快速上手。
- SOP 负责研发可执行流程。
- 状态矩阵负责当前交付状态与测试清单。

以上四份文档出现冲突时，以“代码实际行为”优先，并在当次变更中同步修正文档。
