# 📄 数据契约与实体定义 (Data Schema & Contracts)

本文档总结了系统核心数据模型与 API 响应标准，是前后端数据交换的唯一事实来源。

## 1. 核心实体模型 (Database Models)

### 📈 股票与行情 (Stock & Market Data)
- **Stock (stocks)**：存储静态信息（名称、行业、市值等）。
- **MarketDataCache (market_data_cache)**：
    - **主外键**：`ticker` 关联 `stocks.ticker`。
    - **关键字段**：
        - `current_price` (Float): 最新现价。
        - `change_percent` (Float): 今日涨跌幅。
        - `rsi_14`, `ma_200`, `risk_reward_ratio`: AI 诊断的核心量化指标。
        - `market_status`: `PRE_MARKET`, `OPEN`, `AFTER_HOURS`, `CLOSED`。

### 🤖 AI 诊断报告 (AnalysisReport)
- **存储表**：`analysis_reports`
- **关键结构化字段**：
    - `sentiment_score`: 舆情/技术面综合得分 (0-100)。
    - `immediate_action`: `BUY`, `HOLD`, `SELL`。
    - `target_price`, `stop_loss_price`: 止盈止损线。
    - `entry_zone`: 建议买入区间描述。

### 📁 投资组合 (Portfolio)
- **存储表**：`portfolios`
- **逻辑**：多对多关系的中间态。关联 `User` 与 `Stock`。 `quantity > 0` 为持仓，`quantity = 0` 为观察。

## 2. API 通讯契约 (API Contracts)

### 🟢 标准基础响应
所有 API 错误均遵循以下结构：
```json
{
  "detail": "错误描述",
  "message": "人性化提示 (可选)"
}
```

### 🔵 复合响应：PortfolioSummary
```json
{
  "total_market_value": 1000.0,
  "holdings": [
    {
      "ticker": "AAPL",
      "current_price": 270.0,
      "market_status": "OPEN",
      "risk_reward_ratio": 1.5
    }
  ],
  "sector_exposure": []
}
```

## 3. 开发约束
1. **字段命名**：后端 Python 使用 `snake_case`，前端 TypeScript 中对应字段需保持一致（或在 Pydantic 中配置 alias，目前项目建议保持全链路 `snake_case` 以简化映射）。
2. **Nullable 处理**：金融数据存在缺失风险，所有 Float 类型在 API 输出前必须使用 `sanitize_float` 函数处理。
