# 技术栈与开发规范 (Tech Stack & Development Guidelines)

## 1. 项目概览 (Project Overview)

**名称：** AI 智能投顾助手**Name:** AI Smart Investment Advisor
**Type:** Web Application (SaaS Architecture)
**Goal:** Provide real-time stock tracking and AI-driven investment analysis using RAG (Retrieval-Augmented Generation) & Context Injection concepts.

## 2. 前端技术栈 (Frontend Stack)

-   **框架 (Framework):** Next.js 14+ (App Router 架构).
-   **语言 (Language):** TypeScript (严格模式).
-   **样式 (Styling):**
    -   Tailwind CSS (Utility-first).
    -   `clsx` & `tailwind-merge` (动态类名管理).
-   **UI 组件库:**
    -   **Shadcn/UI** (基于 Radix UI 的无头组件).
    -   **Lucide React** (统一图标库).
-   **数据可视化 (Data Visualization):**
    -   **Recharts** (专用于金融时间序列图表，已定制化).
-   **状态管理与请求:**
    -   React Context (全局用户状态).
    -   SWR (轻量级数据请求与缓存).
    -   Axios (HTTP 客户端，配置了拦截器处理 401/403).
-   **表单处理:**
    -   React Hook Form.
    -   Zod (Schema 校验).

## 3. 后端技术栈 (Backend Stack)

-   **框架 (Framework):** FastAPI (Python).
-   **语言 (Language):** Python 3.10+.
-   **服务器 (Server):** Uvicorn (ASGI).
-   **数据库 ORM:**
    -   **SQLAlchemy (AsyncIO)**: 强制使用异步操作。
    -   **Alembic**: 数据库版本迁移管理 (Migration)。
-   **配置管理:** `pydantic-settings` (环境变量管理).
-   **认证 (Authentication):**
    -   OAuth2 (Bearer JWT).
    -   `python-jose`: JWT 编解码。
    -   `passlib[bcrypt]`: 密码哈希存储。
-   **金融数据引擎 (Market Data Engines):**
    -   `yfinance`: 美股实时行情、历史 K 线。
    -   `akshare`: A 股实时行情 (基于新浪财经接口)。
    -   `pandas` & `pandas_ta`: 计算 RSI, MACD, MA, Bollinger Bands 等技术指标。
-   **AI 集成 (LLM Integration):**
    -   **SiliconFlow API**: 接入 **DeepSeek-R1** / **Qwen2.5-72B** (高性价比推理)。
    -   `google-generativeai`: Google Gemini 官方 SDK (备选)。
-   **搜索增强 (Search Grounding):**
    -   **Tavily API**: 专为 AI 优化的实时网络搜索引擎（用于抓取最新新闻）。

## 4. 数据库架构 (Database Architecture)

-   **当前 (Current):** **SQLite (AsyncIO)**
    -   适用于单用户/开发阶段，部署简单。
    -   启用 WAL 模式 (Write-Ahead Logging) 以支持轻量级并发。
-   **目标 (Target - v2.1+):** **PostgreSQL**
    -   当并发用户 > 5 或需要高频写入时迁移。
    -   支持 `pgvector` 向量存储 (RAG)。

## 5. 项目结构规范 (Directory Structure)

```text
/
├── frontend/                 # Next.js 前端应用
│   ├── app/                  # App Router 页面
│   ├── components/           # UI 组件
│   │   ├── ui/               # Shadcn 基础组件
│   │   └── features/         # 业务组件 (StockChart, StrategyPanel)
│   └── lib/                  # 工具函数 (utils, api, store)
│
├── backend/                  # FastAPI 后端应用
│   ├── app/
│   │   ├── api/              # 路由定义 (v1/endpoints)
│   │   ├── core/             # 核心配置 (config, database, security)
│   │   ├── models/           # SQLAlchemy 数据库模型
│   │   ├── schemas/          # Pydantic 数据模式 (DTO)
│   │   └── services/         # 业务逻辑 (AIService, MarketDataService)
│   ├── scripts/              # 辅助脚本 (auto_refresh.py, init_db.py)
│   └── tests/                # Pytest 测试用例
│
└── doc/                      # 项目文档 (PRD, Flowchart, Migration Plan)
```

## 6. 开发规范 (Development Guidelines)

1.  **强类型 (Strict Typing):** 前后端均需定义完整的 Type/Schema (TypeScript interfaces & Pydantic models)。
2.  **异步优先 (Async First):** 所有 I/O 操作（数据库读写、API 调用）必须使用 `async/await`，禁止阻塞主线程。
3.  **单一真实源 (Single Source of Truth):** 盈亏比 (RRR) 数据以数据库中的 `MarketDataCache` 为准，AI 决策具有最高优先级。
4.  **错误处理 (Error Handling):**
    -   后端：统一捕获异常并返回标准 HTTP 错误码 (4xx/5xx)，不暴露内部 Traceback。
    -   前端：全局拦截 401 跳转登录，Toast 提示操作结果。