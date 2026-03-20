# 🤖 AI Smart Investment Advisor (AI 智能股票策略顾问)

> **AI 投资分析与组合辅助系统**。前端基于 Next.js App Router，后端基于 FastAPI，整合行情、新闻、宏观和 LLM 研判能力。

---

## 🌟 核心特性 (Key Features)

### 1. 🎯 精准量化可视化 (Trade Axis)
- **决策价位锚定坐标系**：摒弃常规等分刻度，采用核心价位驱动（止损/建仓/加码/目标）的非线性坐标轴。
- **视觉冲突规避**：自动处理重合价位（如“止损”与“加码”重合）的渲染逻辑，确保决策点 100% 视觉对齐。

### 2. 🌐 全球宏观热点雷达 (Macro Radar)
- **5 小时自动巡检**：定时全网扫描影响市场的宏观事件、地缘政治风险及货币政策转向。
- **高可用推送体系**：
  - **飞书 BOT 集成**：整点推送 AI 提炼的 3-5 个核心宏观题材及其对持仓标的的穿透分析。
  - **断网/额度降级**：当海外新闻 API (Tavily) 受限时，系统自动切换至 **财联社本地降级数据源** 确保研判永不断流。
  - **智能去重**：针对摘要类消息开启 1 分钟级动态去重，兼顾个股预警的严肃性与快讯的灵活性。

### 3. 🛡️ 大陆环境深度优化 (Mainland China Optimized)
- **零代理数据抓取**：深度利用 `AkShare` 避开 `yfinance` 等海外网络依赖。
- **混合行情引擎**：美股采用腾讯/新浪行情镜像，A股采用东财/网易镜像，确保行情滞后 < 1 分钟。
- **全栈时区管理**：支持从数据库底层到前端 UI 的统一时区偏移配置（UTC+8 默认）。

### 4. 🧠 机构级 AI 研判逻辑 (Deep Analysis)
- **多模型可切换**：支持系统内置模型与用户自定义模型共存，当前系统内置 `DashScope / qwen3.5-plus`，用户登录后可直接设为默认模型。
- **结构化 AI 输出**：个股分析已拆分为 `news_summary`、`fundamental_analysis`、`macro_risk_note` 三段独立文本，避免消息面、基本面和宏观风险混写。
- **盈亏比强制校验**：系统自动计算目标盈利空间与潜在止损空间的比例，并统一以纯数字形式返回，例如 `1.30`、`2.15`。

### 5. 🔍 可解释性 AI (Explainable AI)
- **端到端逻辑溯源**：AI 在输出研判结论时，强制对齐具体的指标数据（如 `[[REF_T2]]` 对应 MACD 动量）。
- **交互式验证**：用户点击结论中的引用标签，前端自动滚动并**高亮闪烁**对应的技术指标卡片，彻底消除“AI 幻觉”。

### 6. 🕒 AI 信号复盘系统 (The Truth Tracker)
- **真实胜率追踪**：自动记录历史 AI 信号及其发布时的时价。
- **实时 P&L 统计**：根据当前市价动态计算每一笔建议的“预期盈亏”，区分“命中” (Hit) 与“回撤” (Drawdown)，建立透明化的信任背书。

---

## 🚀 启动方式

项目现在明确区分两种启动路径：

### 1. 本地开发

适用于本机调试前后端代码。默认使用：

- 前端：Next.js 开发服务器
- 后端：Uvicorn `--reload`
- 数据库：`backend/.env` 中配置的数据库，当前推荐使用 Neon Postgres
- 后台任务：FastAPI 启动后自动挂起常驻调度协程

启动命令：

```bash
./scripts/start.sh dev
```

本地开发前置要求：

- Node.js 24+ 或兼容版本
- Python 3.10+，推荐使用仓库根目录 `.venv`
- 已准备好 `backend/.env`

启动脚本现在会在启动前自动检查 `3000/8000` 端口占用，并复用依赖缓存，避免每次重复安装依赖。

若需要分别启动，也可以手动执行：

```bash
cd backend
../.venv/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

```bash
cd frontend
npm run dev -- -p 3000
```

### 2. 容器化部署

适用于接近生产的部署方式。`docker-compose.yml` 会启动：

- PostgreSQL
- Redis
- FastAPI backend
- Next.js frontend

启动命令：

```bash
./scripts/start.sh docker
```

或直接使用：

```bash
docker compose up --build -d
```

这一路径与本地开发的差异：

- 数据库固定走 PostgreSQL
- 服务通过容器网络互联
- 更接近线上部署结构

> 当前仓库的默认开发形态已经偏向 “应用跑在本机 / 数据库跑在 Neon”。如果你的服务器资源较小，建议继续把数据库托管在 Neon，只让云主机承担前后端服务和调度任务。

### 3. 2G 服务器推荐发布方式 (GitHub 构建 + 服务器仅拉镜像)

为避免服务器卡死，生产建议使用以下路径：

- GitHub Actions 构建并推送镜像到 GHCR
- 服务器仅执行 `docker pull + docker compose up -d`
- 服务器不执行 `npm install / pip install / docker build`

对应文件：

- 工作流：`.github/workflows/deploy.yml`
- 生产编排：`docker-compose.prod.yml`
- 远端部署脚本：`scripts/deploy_compose_prod.sh`

需要在仓库 Secrets 配置：

- `SERVER_IP`
- `SERVER_USER`
- `SSH_PRIVATE_KEY`
- `GHCR_USERNAME`（可用 GitHub 用户名）
- `GHCR_TOKEN`（需要 read:packages 权限）
- `NEXT_PUBLIC_API_URL`（前端构建时注入）

服务器上的 `backend/.env` 需单独维护，不要直接复用本机值。若数据库跑在宿主机而后端跑在容器内，请使用：

- `DATABASE_URL=postgresql+asyncpg://<user>:<pass>@host.docker.internal:5432/<db_name>`

---

## 🛠 系统架构与技术栈

### 前端 (Frontend)
- **核心框架**: Next.js 16 (App Router) + React 19
- **样式方案**: Tailwind CSS (遵循 `Slate/Zinc` 极简金融风)
- **交互组件**: Radix UI + Lucide Icons
- **接口层**: Axios + OpenAPI 生成类型

### 后端 (Backend)
- **核心框架**: FastAPI (Python 3.10+)
- **任务调度**: 常驻后台协程 (轮询精度 60s)
- **数据库**: Neon Postgres / PostgreSQL (SQLAlchemy Async)
- **AI 引擎**: Gemini / SiliconFlow / DashScope，支持系统内置模型与用户模型并存

---

## 📂 项目结构布局

### 后端核心目录
- `backend/app/services/macro_service.py`: 宏观雷达与财联社快讯降级逻辑核心。
- `backend/app/services/notification_service.py`: 飞书 Webhook 签名安全校验与去重算法。
- `backend/app/services/scheduler.py`: 负责整点摘要生成的调度中心。
- `backend/app/services/system_ai_registry.py`: 启动时注册系统内置 AI Provider 与内置模型。
- `backend/app/core/database.py`: 异步 Session 管理逻辑。
- `backend/app/api/v1/endpoints/user.py`: 用户设置、密码修改、AI 连接测试接口。

### 前端核心目录
- `frontend/components/features/StockDetail.tsx`: 包含复杂的交易轴 (Trade Axis) 渲染算法。
- `frontend/features/*/api/*.ts`: 按领域拆分的前端 API 层。
- `frontend/types/schema.d.ts`: 基于后端 OpenAPI 生成的类型定义。
- `frontend/lib/utils.ts`: 全局 `formatDateTime` 时区转换方案。
- `frontend/app/settings/page.tsx`: 左侧导航式设置页，当前包含通用设置、AI 配置、通知、安全、数据管理。

---

## 🤖 AI 模型配置说明

当前系统同时支持两类模型来源：

### 1. 系统内置模型
- 由系统统一注册在 `provider_configs + ai_model_configs`
- 当前默认内置模型：`DashScope / qwen3.5-plus`
- 所有用户登录后都能直接看到并设为默认模型
- 内置模型不允许用户编辑或删除

### 2. 用户自定义模型
- 存储在 `user_ai_models`
- 每条配置独立包含：
  - `base_url`
  - `api_key`
  - `model_id`
  - `provider_note`
- 用户可以新增、编辑、删除，并设为默认

### 3. 个股分析输入源
单次个股 AI 分析仍然只调用 **一次模型**，但会同时喂给模型多类上下文：
- 技术面 `market_data`
- 用户持仓 `portfolio_data`
- 基本面 `fundamental_data`
- 个股新闻 `news_data`
- 宏观上下文 `macro_context`
- 历史分析 `previous_analysis`

为避免消息区和基本面区错位，AI 输出已拆成 3 个字段：
- `news_summary`: 只总结个股新闻流
- `fundamental_analysis`: 只解释估值/行业/基础面
- `macro_risk_note`: 只解释宏观外部风险

因此前端现在可以做到：
- `NEWS` 区块只展示 `news_summary`
- 基本面卡单独展示 `fundamental_analysis`
- 宏观风险单独展示 `macro_risk_note`

---

## ⏱ 调度任务概览

当前后台调度并不会“给数据库里所有股票定时跑 AI 个股分析”。

### 会定时触发 AI 的任务
- **盘后个股复盘**：只针对“用户持仓中的股票”，并且只在对应市场收盘窗口触发
- **每小时新闻摘要**：宏观/快讯类 AI 摘要
- **每日持仓报告**：组合级 AI 分析

### 不会调用个股 AI 的任务
- `refresh_all_stocks()` 只刷新行情、技术指标和缓存

也就是说，当前个股 AI 的定时任务是“用户持仓驱动”，不是“全市场全量轮询”。

---

## 🔄 OpenAPI 类型同步

后端接口变更后，使用下面的流程同步前端类型：

```bash
cd backend
../.venv/bin/python -c 'import json; from app.main import app; open("openapi.json", "w").write(json.dumps(app.openapi(), ensure_ascii=False, indent=2))'
```

```bash
cd frontend
npm run generate-types
```

`frontend/types/index.ts` 只保留 OpenAPI 未覆盖的少量业务扩展类型，用户设置相关类型应优先从生成文件派生。

---

## ⚠️ 部署注意事项

1. 确保 `backend/.env` 中正确配置 `SECRET_KEY`、数据库连接、AI Provider Key、飞书 Webhook 等变量。
2. 如果要启用系统内置 `DashScope / qwen3.5-plus`，至少需要配置：
   - `DASHSCOPE_API_KEY`
   - 可选 `DASHSCOPE_BASE_URL`（默认 `https://coding.dashscope.aliyuncs.com/v1`）
3. 后端启动时会自动执行系统内置模型注册；如果你新增了系统模型定义，重启后端即可写入数据库。
4. 大陆网络环境建议使用镜像源安装依赖：
   - Python: `pip install -i https://pypi.tuna.tsinghua.edu.cn/simple`
   - Node: `npm --registry=https://registry.npmmirror.com`
5. 初始化数据库或补种子数据时，优先使用 `backend/scripts/` 分组目录：
   - `backend/scripts/db/`：数据库初始化、迁移、种子
   - `backend/scripts/data/`：行情/新闻采集与刷新
   - `backend/scripts/dev/`：本地并发与性能诊断
6. 生产部署优先使用 Docker Compose，不建议直接运行开发态脚本。

---

## 🗄️ 数据库迁移与安全 (Database Migrations)

本项目使用 Alembic 进行结构管理。为了确保 Neon 主库的安全，必须遵循以下纪律：

1. **结构变更流**：本地修改模型 -> 生成 Migration -> 在 Neon 临时分支验证 -> 确认无误后合并至主库。
2. **禁止手动改表**：禁止直接在 Neon Console 或 SQL 客户端手动修改 Schema，所有变更必须有 Alembic 脚本。
3. **部署前置**：在生产环境重启服务前，必须先执行 `alembic upgrade head`。

若遇到依赖冲突（如 `DependentObjectsStillExistError`），请检查外键删除顺序，并优先在临时分支复现。

---

## 🔗 数据源致谢
- 金融数据: AKShare
- 实时快讯: 财联社 (Cailianshe)
- 搜索支持: Tavily API

---
© 2026 AI Smart Investment Advisor - 让决策更理智。
