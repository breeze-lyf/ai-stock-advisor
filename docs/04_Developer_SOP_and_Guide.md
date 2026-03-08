# 04. 开发者 SOP 与代码指南 (Developer SOP & Guidelines)

**定位：** 本文档旨在保证在多人协同开发或接手本全栈项目时，能保持代码风格的高度一致性，尤其是涉及到最核心的“量化逻辑变更”和“UI组件拆解”时。

---

## 1. 结构与分层红线 (Architecture Rules)

### 1.1 前端 (Next.js 14) 的三层组件哲学
为了避免诸如早期的 `StockDetail.tsx` (1255行) 那样的“面条代码巨兽”，我们确立了强制的三层原子化结构：

| 层级 | 示例目录 | 核心职责 | 状态管理规则 |
| :--- | :--- | :--- | :--- |
| **01 编排层 (Orchestration)** | `app/stock/[ticker]/page.tsx` 或 `StockDetail.tsx` (入口) | 全局路由参数解析、全局数据 Fetch (SWR)、子组件布局编排。 | 可以使用 hooks，向下钻取 Props。 |
| **02 业务层 (Functional Blocks)** | `components/features/stock-detail/` (如 `AIVerdict.tsx`) | 具体业务逻辑展示（如 AI 分析面板、交易重轴线）。 | **严禁**在内部再次调用独立 fetch，强依赖 props (定义在 `types.ts` 中)。 |
| **03 原子 UI 层 (Atomic UI)** | `components/ui/` (如 `button`, `badge`) | 纯粹的 UI 展示组件。 | 绝对的无状态组件 (Stateless)。 |

### 1.2 后端 (FastAPI) 的指责下沉法则
*   **Router 只是门面**: `api/v1/endpoints/*.py` 严禁出现实际的数据处理逻辑。仅仅起到 `@router.get`、参数提取的作用。
*   **Service 才是核心**: 计算移动平均线、封装 LLM 提示词、聚合 RAG 资料，统统放在 `services/`。
*   **全局单例**: 所有的数据库 `Session` 与第三方驱动必须通过依赖注入 `Depends()` 提供，防止并发泄露。

---

## 2. 核心 SOP: 如何安全地新增一个量化指标？

如果你想在系统中新加一个指标，例如 **“换手率 (Turnover Rate)”**，请严格遵守以下 6 步链路进行全栈打通：

1.  **供应商层 (Provider)**: 
    *   修改 `backend/app/services/market_providers/akshare.py` (或 yfinance)。在抓取的数据帧中摘出换手率。
2.  **模型层 (Model)**: 
    *   在 `backend/app/models/stock.py` 中的 `MarketDataCache` 新增 `turnover_rate = Column(Float)`。
    *   执行 Alembic 迁移更新数据库：`alembic revision --autogenerate -m "add turnover"` -> `alembic upgrade head`。
3.  **服务层 (Service)**: 
    *   在 `backend/app/services/market_data.py` 中的数据组装环节，对换手率数据进行 `sanitize_float` (防御 NaN)。
4.  **接口层 (Schema)**: 
    *   在 `backend/app/schemas/portfolio.py` 的 Pydantic 输出模型中新增对应的属。
5.  **前端类型同步 (Frontend Types)**: 
    *   打开 `frontend/types/index.ts`，在对应的 TS Interface 里加入 `turnover_rate: number | null`。
6.  **UI 渲染 (UI Components)**: 
    *   将该字段展示在某个具体的 Functional Block，如 `TechnicalInsights.tsx`。

---

## 3. 强类型与容错规范 (Robustness)

*   **TypeScript 无 Any 政策**: 严禁在核心业务组件使用 `any`。哪怕后端返回未知 JSON，也要用 `Record<string, unknown>` 兜底。
*   **RAG 数据漂移防御**: 因为三方接口（特别是雅虎财经的盘前时段）极其不稳定，所有抓取过来的 Float 参数写入数据库前，必须经过防御性包裹：
    ```python
    def sanitize_float(val: Any) -> float | None:
        if pd.isna(val) or val is None or val == "N/A":
            return None
        return float(val)
    ```
