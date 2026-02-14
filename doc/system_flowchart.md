# 系统架构：数据处理流程

本文档详细说明了 AI 智能投顾系统内的数据流转，涵盖市场数据摄入、AI 分析以及自动刷新周期。

```mermaid
flowchart TD
    %% Nodes
    User["用户/客户端"]
    AutoRefresh["自动刷新脚本<br/>(后台任务)"]
    API["API 层<br/>(FastAPI)"]
    
    subgraph Services [核心服务]
        MDS["市场数据服务<br/>(MarketDataService)"]
        AIS["AI 服务<br/>(AIService)"]
        NewsService["新闻聚合器"]
    end
    
    subgraph Providers [外部供应商]
        YF["YFinance<br/>(雅虎财经)"]
        AK["AkShare<br/>(A股数据)"]
        TV["Tavily<br/>(智能搜索)"]
        LLM["大模型供应商<br/>(SiliconFlow / Gemini)"]
    end
    
    subgraph Database [数据持久化]
        DB["SQLite 数据库"]
        StockTable["股票表"]
        CacheTable["市场数据缓存表"]
        NewsTable["股票新闻表"]
    end

    %% Flows
    
    %% 1. Triggering Data Fetch
    User -- "请求: GET /api/stocks/{ticker}" --> API
    API -- "1. 调用 get_real_time_data" --> MDS
    
    AutoRefresh -- "循环: 查找最久未更新股票" --> DB
    DB -- "返回 Ticker" --> AutoRefresh
    AutoRefresh -- "2. 调用 get_real_time_data (强制刷新)" --> MDS
    
    %% 2. Market Data Service Logic
    MDS -- "检查缓存" --> CacheTable
    CacheTable -- "返回数据" --> MDS
    
    MDS -- "缓存未命中或强制刷新" --> FetchProvider{选择供应商}
    FetchProvider -- "美股" --> YF
    FetchProvider -- "A股" --> AK
    
    %% 3. Parallel Fetching
    YF & AK -- "获取报价" --> MDS
    YF & AK -- "获取基本面" --> MDS
    YF & AK -- "获取历史K线 (指标计算)" --> MDS
    YF & AK -- "获取新闻" --> MDS
    
    %% 4. Data Processing & Persistence
    MDS -- "计算技术指标<br/>(RSI, MACD, MA, 布林带)" --> MDS
    MDS -- "更新" --> DB
    MDS -- "插入/更新新闻" --> NewsTable
    
    %% 5. RRR Logic (Strict)
    MDS -- "检查 is_ai_strategy 标志" --> CacheTable
    CacheTable -- "是 AI 策略" --> RRR_AI["锁定支撑/阻力位<br/>动态重算盈亏比"]
    CacheTable -- "非 AI 策略" --> RRR_Tech["使用技术指标更新支撑/阻力<br/>强制设置盈亏比 = None"]
    RRR_AI & RRR_Tech -- "提交事务" --> CacheTable

    %% 6. AI Analysis Flow
    User -- "请求: POST /api/analysis/{ticker}" --> API
    API -- "3. 触发分析" --> AIS
    
    AIS -- "获取上下文" --> MDS
    MDS -- "获取实时数据" --> AIS
    
    AIS -- "获取外部上下文" --> NewsService
    NewsService -- "搜索新闻" --> TV
    TV -- "返回上下文" --> AIS
    
    AIS -- "构建提示词<br/>(数据 + 新闻 + 策略)" --> LLM
    LLM -- "返回分析 JSON" --> AIS
    
    AIS -- "解析响应" --> API
    
    %% 7. Sync Back to Cache
    API -- "保存分析结果" --> DB
    API -- "同步策略至缓存" --> CacheTable
    CacheTable -- "设置 is_ai_strategy=True<br/>设置 目标价/止损价" --> CacheTable
```

## 流程说明

1.  **触发机制 (Triggers)**:
    *   **用户请求**: 通过前端进行直接交互（查看个股或请求 AI 诊断）。
    *   **自动刷新脚本**: 一个后台常驻进程，每 5 分钟轮询一次“最陈旧”（`last_updated` 时间最早）的股票，强制刷新数据。

2.  **市场数据获取 (`MarketDataService`)**:
    *   **缓存优先**: 始终先检查 `MarketDataCache` 表，最小化 API 调用。
    *   **供应商路由**: 根据股票代码格式，自动路由至 `YFinance` (美股) 或 `AkShare` (A股)。
    *   **并发抓取**: 使用 `asyncio.gather` 并行获取报价、基本面、历史K线（用于计算指标）和新闻。

3.  **严格逻辑执行 (Strict Logic Enforcement)**:
    *   **盈亏比 (RRR)**: 系统强制执行“单一真实数据源”原则。
        *   如果 `is_ai_strategy` 为 **True**，则忽略技术指标计算的盈亏比。系统锁定 AI 提供的目标价和止损价，纯粹基于当前实时价格动态重算比例。
        *   如果 `is_ai_strategy` 为 **False**，强制将盈亏比设为 `None`，防止通用技术算法产生的数值误导用户。

4.  **AI 智能分析 (`AIService`)**:
    *   **上下文聚合**: 组合实时市场数据与外部新闻（通过 `Tavily` 或供应商新闻）。
    *   **LLM 推理**: 发送结构化 Prompt 给大模型 (DeepSeek/Qwen) 以生成交易计划。
    *   **反馈闭环**: 经用户批准的 AI 计划（目标价/止损价）会被回写到 `MarketDataCache`，并将 `is_ai_strategy` 标记为 `True`，从而影响未来的数据更新逻辑。
