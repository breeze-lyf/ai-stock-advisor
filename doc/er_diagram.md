# 数据库 ER 图与数据字典 (ER Diagram & Data Dictionary)

本项目后端使用 SQLite (本地开发) 或 PostgreSQL (生产) 数据库。以下是核心实体关系图及详尽的数据字典。

## 1. 实体关系图 (ER Diagram)

```mermaid
erDiagram
    USERS ||--o{ PORTFOLIOS : "管理"
    USERS ||--o{ ANALYSIS_REPORTS : "生成/查看"
    STOCKS ||--|| MARKET_DATA_CACHE : "拥有 (1:1)"
    STOCKS ||--o{ STOCK_NEWS : "包含"
    STOCKS ||--o{ PORTFOLIOS : "被持有"
    STOCKS ||--o{ ANALYSIS_REPORTS : "被诊断"

    USERS {
        string id PK "用户UUID"
        string email "邮箱 (登录凭证)"
        string hashed_password "加密后的密码"
        boolean is_active "是否激活"
        string membership_tier "会员等级 (FREE/PRO)"
        string api_key_gemini "Gemini API密钥"
        string api_key_deepseek "DeepSeek API密钥"
        string api_key_siliconflow "硅基流动 API密钥"
        string preferred_data_source "首选数据源"
        string preferred_ai_model "首选AI模型"
        datetime created_at "创建时间"
        datetime last_login "最后登录"
    }

    STOCKS {
        string ticker PK "股票代码 (如 AAPL)"
        string name "股票名称"
        string sector "板块"
        string industry "细分行业"
        float market_cap "市值"
        float pe_ratio "市盈率"
        float eps "每股收益"
        string exchange "交易所"
        string currency "货币单位"
    }

    MARKET_DATA_CACHE {
        string ticker PK, FK "股票代码"
        float current_price "现价"
        float change_percent "涨跌幅"
        float rsi_14 "RSI指标"
        float macd_val "MACD值"
        float risk_reward_ratio "实时盈亏比"
        boolean is_ai_strategy "是否启用AI锁定点位"
        datetime last_updated "最后同步时间"
    }

    PORTFOLIOS {
        string id PK "记录唯一ID"
        string user_id FK "关联用户"
        string ticker FK "关联股票"
        float quantity "持有数量"
        float avg_cost "持仓成本"
        float target_price "手动设置的目标价"
        float stop_loss_price "手动设置的止损价"
        datetime updated_at "更新时间"
    }

    ANALYSIS_REPORTS {
        string id PK "报告ID"
        string user_id FK "用户"
        string ticker FK "股票"
        string sentiment_score "情绪偏差 (0-100)"
        string summary_status "诊断状态短语"
        text action_advice "AI 操作建议"
        float target_price "AI 建议止盈位"
        float stop_loss_price "AI 建议止损位"
        string model_used "使用的模型"
        datetime created_at "报告生成时间"
    }

    STOCK_NEWS {
        string id PK "新闻来源ID"
        string ticker FK "关联股票"
        string title "新闻标题"
        string link "原文URL"
        datetime publish_time "发布时间"
        string sentiment "AI 情感倾向"
    }
```

## 2. 详尽数据字典 (Data Dictionary)

### 2.1 用户表 (Users)

| 字段名 | 类型 | 描述 | 数据来源 | 数据去向 |
| :--- | :--- | :--- | :--- | :--- |
| `id` | UUID | 唯一标识 | 系统生成 | 各关联表外键 |
| `email` | String | 登录邮箱 | 用户注册 | 身份认证 |
| `hashed_password` | String | 加密密码 | 用户注册 | 登录验证 |
| `api_key_siliconflow` | String | 硅基流动密钥 | 用户设置 | 后端 AI 调用 |
| `preferred_ai_model` | String | 默认 AI 模型 | 用户设置 | 触发诊断请求 |

### 2.2 股票基础信息表 (Stocks)

| 字段名 | 类型 | 描述 | 数据来源 | 数据去向 |
| :--- | :--- | :--- | :--- | :--- |
| `ticker` | String | 股票代码 | 交易所/yfinance | 全局搜索与索引 |
| `name` | String | 股票全称 | yfinance/API | 前端显示 |
| `sector` | String | 行业板块 | yfinance | 组合风险分析 |
| `market_cap` | Float | 市值 | yfinance | AI 提示词上下文 |

### 2.3 行情与指标缓存表 (Market_Data_Cache)

| 字段名 | 类型 | 描述 | 数据来源 | 数据去向 |
| :--- | :--- | :--- | :--- | :--- |
| `current_price` | Float | 当前成交价 | 实时 API (yfinance) | 盈亏计算/图标显示 |
| `risk_reward_ratio` | Float | 盈亏比 | 算法计算 | 侧边栏 R/R 标签 |
| `resistance_1` | Float | 压力位 (R1/Target) | 技术算法 / AI 诊断 | 交易中轴线渲染 |
| `support_1` | Float | 支撑位 (S1/Stop) | 技术算法 / AI 诊断 | 交易中轴线渲染 |
| `is_ai_strategy` | Boolean | AI 策略锁定标识 | 系统状态 | 防止通用算法覆盖 AI 点位 |

### 2.4 持仓/自选表 (Portfolios)

| 字段名 | 类型 | 描述 | 数据来源 | 数据去向 |
| :--- | :--- | :--- | :--- | :--- |
| `user_id` | UUID/String | 所属用户 | 会话/Token | 权限校验 |
| `quantity` | Float | 持有股数 | 用户输入 | 盈亏计算 |
| `avg_cost` | Float | 持仓成本价 | 用户输入 | 盈亏率计算 |

### 2.5 AI 分析报告表 (Analysis_Reports)

| 字段名 | 类型 | 描述 | 数据来源 | 数据去向 |
| :--- | :--- | :--- | :--- | :--- |
| `sentiment_score` | String | 情绪偏好得分 | SiliconFlow AI 结果 | 情绪偏差仪表盘 |
| `action_advice` | Text | AI 核心操作建议 | SiliconFlow AI 结果 | 诊断详情主要文案 |
| `target_price` | Float | AI 建议止盈价 | AI 结构化输出 | 更新 `market_data_cache` |
| `stop_loss_price` | Float | AI 建议止盈价 | AI 结构化输出 | 更新 `market_data_cache` |
| `model_used` | String | 所用模型 ID | 请求参数 | 历史记录追溯 |

## 3. 业务逻辑流转 (Data Flow Hints)

1. **行情流**：`yfinance/API` -> `market_data_cache` -> `Frontend (实时更新)`。
2. **诊断流**：`market_data_cache` + `Stocks (上下文)` -> `SiliconFlow API` -> `Analysis_Reports` -> `market_data_cache (反向更新点位)`。
3. **资产流**：`Portfolio` + `market_data_cache (current_price)` -> `Frontend (持仓总资产对比)`。
