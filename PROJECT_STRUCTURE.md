# AI Stock Advisor 全系统深度架构文档

## 1. 软件架构全景图 (Software Architecture Topography)

系统采用高度解耦的微服务化思想（虽然部署在单机），分为四层架构：

### 1.1 表现层 (Presentation Layer)

- **技术栈**: Next.js 14+, TypeScript, TailwindCSS.
- **核心组件**:
  - `PortfolioList`: 实时持仓监控与 RRR 动态标签展示。
  - `StockDetail`: 股票详情、ECharts K线图、AI 研判可视化（Trade Axis）。
  - `SearchDialog`: 跨市场股票搜索与自选添加。

### 1.2 接口层 (API Gateway / Route Layer)

- **技术栈**: FastAPI, Pydantic.
- **职责**: 路由分发、JWT 身份校验、全局异常捕获、数据格式序列化（NaN 清洗）。

### 1.3 业务逻辑层 (Service/Logic Layer)

- **行情适配 (Market Providers)**: `ProviderFactory` 动态调度 `YFinance` (美股) 与 `AkShare` (A股)。
- **指标引擎 (Technical Indicator Engine)**: `TechnicalIndicators` 基于 Pandas 手动实现 (适配 Python 3.14+)。
- **研判大脑 (AI Service)**: 调度 LLM 生成结构化投资策略，执行模型降级与 Token 校验。

### 1.4 数据持久化层 (Persistence Layer)

- **技术栈**: SQLAlchemy (Async), Alembic, SQLite.
- **模式**: WAL (Write-Ahead Logging) 模式，解决文件锁争用。

---

## 2. 数据库详细设计 (Entity-Relationship & Schema)

### 2.1 用户表 (`users`)

存储用户身份、偏好与 API 秘钥。
| 字段名 | 类型 | 解释 |
| :--- | :--- | :--- |
| `id` | UUID (String) | 主键 |
| `email` | String | 登录唯一邮箱 (Indexed) |
| `hashed_password` | String | 加密后的密码 |
| `membership_tier` | Enum | 成员等级 (FREE/PRO) |
| `api_key_gemini` | String | 用户自备的 Gemini Key |
| `preferred_ai_model` | String | 首选分析模型 |

### 2.2 股票元数据表 (`stocks`)

存储股票的静态基本面数据。
| 字段名 | 类型 | 解释 |
| :--- | :--- | :--- |
| `ticker` | String (PK) | 唯一代码 (如 `AAPL`, `600519.SH`) |
| `name` | String | 股票中文/英文简称 |
| `sector`/`industry` | String | 所属板块与细分行业 |
| `market_cap` | Float | 总市值 |
| `pe_ratio`/`eps` | Float | 市盈率/每股收益 |

### 2.3 实时数据缓存表 (`market_data_cache`)

**核心表**，存储技术指标与最新价格，每 2-5 分钟更新。
| 字段名 | 类型 | 解释 | 数据来源 |
| :--- | :--- | :--- | :--- |
| `current_price` | Float | 最新成交价 | yfinance/akshare |
| `change_percent` | Float | 涨跌幅 | yfinance/akshare |
| `rsi_14` | Float | 相对强弱指标 | TechnicalIndicators |
| `macd_val/signal` | Float | MACD 核心值 | TechnicalIndicators |
| `bb_upper/lower` | Float | 布林带通道上下轨 | TechnicalIndicators |
| `support_1/2` | Float | 关键支撑位 (S1, S2) | Pivot Calculation |
| `resistance_1/2` | Float | 关键阻力位 (R1, R2) | Pivot Calculation |
| `risk_reward_ratio` | Float | **盈亏比 (RRR)** | 三级回退逻辑计算 |
| `last_updated` | DateTime | 最后抓取时间 | 系统时间 |

---

## 3. 字段级数据流映射 (Field-Level Data Flow Matrix)

下表展示了一个核心指标（如 RRR）是如何从原始行情变成 UI 标签的：

| 阶段                | 处理过程                                                                         | 涉及字段/组件                          |
| :------------------ | :------------------------------------------------------------------------------- | :------------------------------------- |
| **1. 原始数据获取** | yfinance/akshare 抓取 6 个月历史 OHLCV。                                         | `pandas.DataFrame`                     |
| **2. 指标计算**     | `TechnicalIndicators` 计算 Pivot Points、Bollinger Bands。                       | `R1`, `S1`, `BB_Upper`, `BB_Lower`     |
| **3. RRR 逻辑判定** | 三级回退：(1) (R1-Price)/(Price-S1) (2) 若失效则用 BB (3) 若再失效用 MA50±2ATR。 | `risk_reward_ratio`                    |
| **4. 持久化**       | 写入 `market_data_cache` 表，替换旧值。                                          | `market_data_cache.risk_reward_ratio`  |
| **5. API 聚合**     | `get_portfolio` 接口 JOIN `portfolios` 与 `market_data_cache`。                  | `PortfolioItem` Schema                 |
| **6. 前端渲染**     | `PortfolioList.tsx` 检测 `rrr >= 3.0` 渲染 Emerald Badge。                       | `<Tooltip>` + `item.risk_reward_ratio` |

---

## 4. 关键功能点解析 (Feature Deep-Dive)

### 4.1 自动行情同步机制

- **进入页面**: 触发 `fetchData(refresh=false)` -> 后端优先读 Cache。
- **点击刷新**: 触发 `fetchData(refresh=true)` -> 后端强制调用 `Provider` 抓取并重新计算全量指标。
- **并发控制**: 后端使用 `asyncio.gather` 并发处理多支股票，提升多资产刷新效率。

### 4.2 AI 结构化研判系统

- **输入端**: 注入 `Stock` 元数据 + `MarketDataCache` 实时指标 + `provider.get_news()`。
- **推理端**: Prompt 强制 AI 返回 JSON，包含 `entry_price_high` (建仓上限) 等 15 个结构化字段。
- **输出端**: `AnalysisReport` 表持久化 Response。前端 `StockDetail` 采用可视化进度条（Trade Axis）展示建仓/止损/止盈区间。

### 4.3 极致稳定性设计

- **SQLite WAL**: 读写分离日志，解决多线程写数据库导致的 `Database is locked` 报错。
- **NaN 清洗器**: 在 `stock.py` 路由末端执行 `_sanitize_ohlcv`，将所有 `NaN/Inf` 转换成 `null`，防止前端 Axios 崩溃。
- **接口指数退避**: 前端 `api.ts` 捕获 5xx 或 Network Error 后，自动等待 1s, 2s 后发起最多 2 次重试。

---

## 5. 项目骨架 (Folder Manifest)

```text
/backend
  ├── app
  │   ├── api/v1       - 终端节点 (analysis, portfolio, stock, auth)
  │   ├── core         - 基础设施 (database-WAL, security-JWT, config-ENV)
  │   ├── models       - 数据库实体 (SQLAlchemy)
  │   ├── schemas      - 数据交换规范 (Pydantic models)
  │   └── services     - 核心算法 (AI 提示词、行情分发器、技术指标引擎)
  └── scripts          - 数据库初始化与迁移脚本
/frontend
  ├── app              - Next.js App Router (主路径与设置页)
  ├── components/ui    - ShadcnUI 基础样式组件
  ├── components/features - 业务重度组件 (PortfolioList, StockDetail)
  └── lib              - 全局单例 (api-retry-client, utils)
```
