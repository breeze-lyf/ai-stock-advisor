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
- **DeepSeek-R1 驱动**：使用 SiliconFlow 高速接口进行深度逻辑推演，重点捕捉趋势拐点与极端情绪。
- **盈亏比强制校验**：系统自动计算目标盈利空间与潜在止损空间的比例，低于 `1:1.5` 的机会将强标为“低性价比”。

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
- 数据库：本地 `.env` 中配置的数据库，默认 SQLite
- 后台任务：本地 `auto_refresh_market_data.py`

启动命令：

```bash
./scripts/start.sh dev
```

本地开发前置要求：

- Node.js 24+ 或兼容版本
- Python 3.10+，推荐使用仓库根目录 `.venv`
- 已准备好 `backend/.env`

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
- **数据库**: SQLite / PostgreSQL (SQLAlchemy Async)
- **AI 引擎**: SiliconFlow / Gemini，多 provider fallback

---

## 📂 项目结构布局

### 后端核心目录
- `backend/app/services/macro_service.py`: 宏观雷达与财联社快讯降级逻辑核心。
- `backend/app/services/notification_service.py`: 飞书 Webhook 签名安全校验与去重算法。
- `backend/app/services/scheduler.py`: 负责整点摘要生成的调度中心。
- `backend/app/core/database.py`: 异步 Session 管理逻辑。
- `backend/app/api/v1/endpoints/user.py`: 用户设置、密码修改、AI 连接测试接口。

### 前端核心目录
- `frontend/components/features/StockDetail.tsx`: 包含复杂的交易轴 (Trade Axis) 渲染算法。
- `frontend/lib/api.ts`: 前端统一 API 客户端与鉴权拦截器。
- `frontend/types/schema.d.ts`: 基于后端 OpenAPI 生成的类型定义。
- `frontend/lib/utils.ts`: 全局 `formatDateTime` 时区转换方案。
- `frontend/app/settings/page.tsx`: 全局用户信息与时区偏好配置。

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
2. 大陆网络环境建议使用镜像源安装依赖：
   - Python: `pip install -i https://pypi.tuna.tsinghua.edu.cn/simple`
   - Node: `npm --registry=https://registry.npmmirror.com`
3. 初始化数据库或补种子数据时，优先使用 `backend/scripts/` 下脚本。
4. 生产部署优先使用 Docker Compose，不建议直接运行开发态脚本。

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
