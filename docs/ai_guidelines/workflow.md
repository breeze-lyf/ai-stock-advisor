# 🛠️ 标准开发 SOP (Workflow & SOP)

本文档为开发新功能（如：新增量化指标、新分析维度）提供了标准的操作规程。

## 1. 新增量化指标的标准路径

如果要为系统新增一个“换手率 (Turnover Rate)”指标并同步到前端：

1.  **数据层 (Provider)**：
    - 修改 `backend/app/services/market_providers/akshare.py`。
    - 在抓取逻辑中增加该字段映射。
2.  **模型层 (Model)**：
    - 修改 `backend/app/models/stock.py` 中的 `MarketDataCache`，增加 `turnover_rate` 字段。
    - 运行 Alembic 迁移（如适用）或本地数据库重置。
3.  **计算层 (Service)**：
    - 修改 `backend/app/services/market_data.py` 中的 `_update_database`，确保新数据被正确存储并经过 `sanitize_float`。
4.  **接口层 (Schema/Router)**：
    - 更新 `backend/app/schemas/portfolio.py` 中的 `PortfolioItem` Pydantic 模型。
5.  **前端交互层 (lib/api & Types)**：
    - 更新 `frontend/types/index.ts` 中的接口定义。
6.  **UI 表现层 (Components)**：
    - 在 `frontend/components/features/StockDetail.tsx` 中添加展示逻辑。

## 2. 强制测试要求 (Verification)

**“无测试，不提交”**。

- 在修改 `market_providers` 后，必须运行对应的 `diagnostic_xxx.py` 脚本或在 `backend` 下新建临时脚本验证数据抓取是否成功。
- **示例命令**：
  ```bash
  python3 backend/diagnostic_us_premarket_v4.py
  ```

## 3. 部署与环境

- 开发环境：建议本地 `localhost:3000` (前端) 和 `8000` (后端)。
- 代理策略：由于后端部署在上海，国内 A 股行情必须强制使用 `bypass_proxy` 逻辑（已集成在 AkShareProvider 中）。
