# AI 分析增强页面 - 架构与实现指南

**文档版本：** v1.0  
**更新日期：** 2026-04-09  
**目标：** 实现无幻觉的 AI 增强分析页面

---

## 第一部分：架构设计

### 1.1 要做什么（功能清单）

| 模块 | 做什么 | 数据来源 | Agent 参与程度 |
|------|-------|---------|---------------|
| ① 判研卡 | 展示操作建议、信心分解 | 现有 AI 分析 | 已有，无需改动 |
| ② 关键假设断点 | 列出策略失效的条件 | 规则引擎 + AI 格式化 | AI 仅润色文字 |
| ③ 催化剂时间轴 | 未来 30 天重大事件 | 混合架构 | 部分使用 Agent |
| ④ 组合联动视角 | 加仓对组合的影响 | 数据库计算 | 不使用 Agent |

**不做：** 历史信号命中率（数据积累不足）

---

### 1.2 核心原则：零幻觉数据流

```
┌─────────────────────────────────────────────────────────┐
│              零幻觉数据流                                 │
│                                                         │
│  真实数据 → AI 格式化 → 前端展示                         │
│     ↑           ↑                                       │
│  不能编造     不能改写数值                               │
│                                                         │
│  ✅ 正确：输入价格$305 → 输出"当前$305"                  │
│  ❌ 错误：输入价格$305 → 输出"当前$310"                  │
└─────────────────────────────────────────────────────────┘
```

**所有数据必须标注：**
- `verified: true` — 来自可信源（API、官方日历），前端直接显示
- `verified: false` — 来自 Agent 搜索，前端显示"需验证"标签

---

### 1.3 整体架构图

```
┌─────────────────────────────────────────────────────────┐
│                    用户请求                               │
│  "获取 GOOGL 的增强分析"                                  │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│              任务编排器 (Orchestrator)                   │
│  职责：拆解任务、分发、聚合结果                          │
│  文件：enhanced_analysis.py                             │
└─────────────────────────────────────────────────────────┘
           │              │              │
           ↓              ↓              ↓
    ┌──────────  ┌──────────┐  ┌──────────────┐
    │ 催化剂   │  │ 关键假设 │  │ 组合联动     │
    │ 聚合器   │  │ 生成器   │  │ 分析器       │
    └──────────  └──────────┘  └──────────────┘
           │              │              │
           ↓              ↓              ↓
    ┌──────────┐  ┌──────────┐  ┌──────────────┐
    │ Yahoo    │  │ 规则引擎 │  │ 数据库       │
    │ FOMC     │  │ AI 格式化│  │ 计算         │
    │ Tavily   │  │          │  │              │
    └──────────┘  └──────────┘  └──────────────┘
           │              │              │
           └──────────────┴──────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                 统一 JSON 输出                            │
│  {verdict, assumptions, catalysts, linkage, _metadata}  │
└─────────────────────────────────────────────────────────┘
```

---

### 1.4 架构类型：工具增强型 Agent

**为什么选这个架构？**

| 方案 | 优点 | 缺点 | 本项目选择 |
|------|------|------|-----------|
| 纯 AI 生成 | 简单 | 一定会幻觉 | ❌ |
| 纯 API 调用 | 准确 | 不灵活 | ❌ |
| **工具增强型** | 准确 + 灵活 | 实现稍复杂 | ✅ |

**核心思想：**
- AI 不是直接回答，而是**调用工具**获取真实数据
- 每个工具都有明确的输入输出契约
- 最终结果必须标注**数据来源**和**验证状态**

---

## 第二部分：任务拆解流程

### 2.1 通用拆解流程（6 步）

```
步骤 1: 意图识别 → 确定需要哪些数据
步骤 2: 任务拆解 → 拆成多个子任务
步骤 3: 工具选择 → 每个子任务选合适的工具
步骤 4: 并行执行 → 同时调用多个工具
步骤 5: 结果聚合 → 合并所有结果
步骤 6: 格式输出 → 统一 JSON 格式
```

---

### 2.2 模块 1：催化剂时间轴 - 任务拆解

**用户请求：** "搜索 GOOGL 未来 30 天的催化剂事件"

#### 步骤 1: 意图识别

需要三类数据：
- 财报日期（结构化数据 → API）
- FOMC 会议（固定日历 → 硬编码）
- 产品发布会（非结构化 → Agent 搜索）

#### 步骤 2: 任务拆解

```
任务 1: 获取财报日期 → Yahoo Finance API
任务 2: 获取 FOMC 日期 → 硬编码日历
任务 3: 搜索产品发布会 → Tavily 搜索 + AI 摘要
```

#### 步骤 3: 工具选择

```python
tools = {
    "任务 1": YahooFinanceTool(),
    "任务 2": FEDCalendarTool(),
    "任务 3": TavilySearchTool() + AIFormatter(),
}
```

#### 步骤 4: 并行执行

```python
import asyncio

results = await asyncio.gather(
    fetch_earnings(ticker),       # 任务 1
    fetch_fomc_dates(),           # 任务 2
    search_product_events(ticker) # 任务 3
)
```

#### 步骤 5: 结果聚合

```python
catalysts = []
catalysts.extend(results[0])  # 财报
catalysts.extend(results[1])  # FOMC
catalysts.extend(results[2])  # 产品发布会
catalysts.sort(key=lambda x: x["date"])  # 按日期排序
```

#### 步骤 6: 格式输出

```json
[
    {
        "date": "2026-04-26",
        "event": "Q1 2026 财报",
        "type": "earnings",
        "impact": "高",
        "verified": true,
        "source": "yfinance"
    },
    {
        "date": "2026-05-14",
        "event": "Google I/O 2026",
        "type": "company_event",
        "impact": "中",
        "verified": false,
        "source": "tavily_search"
    }
]
```

---

### 2.3 模块 2：关键假设断点 - 任务拆解

**用户请求：** "生成 GOOGL 的关键假设断点"

#### 拆解流程

```
步骤 1: 获取真实行情数据 → MarketDataService
  输出：{current_price: 305, ma_20: 300, vix: 21.4, ...}

步骤 2: 获取 AI 分析结果 → AnalysisService
  输出：{stop_loss_price: 295, target_price: 320, ...}

步骤 3: 规则引擎生成假设
  - 如果 ma_20 存在 → 生成均线支撑假设
  - 如果 stop_loss 存在 → 生成止损位假设
  - 如果 vix > 25 → 生成宏观局势假设

步骤 4: AI 格式化（可选）
  如果假设少于 2 个，让 AI 补充一个（但必须基于真实数据）

步骤 5: 输出
```

#### 输出格式

```json
[
    {
        "id": 1,
        "assumption": "20 日均线不被有效跌破",
        "trigger": "收盘价连续 2 日低于 $299.80",
        "consequence": "视为趋势转弱信号，本次建仓计划终止",
        "current_status": "当前距离 -2.1%",
        "risk_level": "核心假设",
        "_verified": true,
        "_data_source": "market_data"
    }
]
```

---

### 2.4 模块 3：组合联动视角 - 任务拆解

**用户请求：** "如果加仓 10 股 GOOGL，对组合有什么影响"

#### 拆解流程

```
步骤 1: 获取当前持仓列表 → Portfolio 表
  输出：[{ticker: "AAPL", market_value: 10000, ...}, ...]

步骤 2: 计算当前总市值
  输出：total_value = 50000

步骤 3: 计算当前行业敞口
  输出：{"Technology": 37.6%, "Industrials": 14.2%, ...}

步骤 4: 计算加仓后的变化
  输出：{"Technology": {"before": 37.6, "after": 52.4}, ...}

步骤 5: 生成警告
  输出：["科技敞口超过建议上限 40%"]

步骤 6: 计算 Beta 变化
  输出：{"before": 1.12, "after": 1.19}
```

#### 输出格式

```json
{
    "sector_exposure": {
        "Technology": {"before": 37.6, "after": 52.4},
        "Industrials": {"before": 14.2, "after": 12.3}
    },
    "beta_change": {"before": 1.12, "after": 1.19},
    "warnings": ["科技敞口超过建议上限 40%"],
    "recommended_max_position": 3.5
}
```

---

## 第三部分：实现指南

### 3.1 后端文件结构

```
backend/app/
├── services/
│   ├── catalyst_aggregator.py      # 催化剂聚合器
│   ├── assumption_generator.py     # 关键假设生成器
│   └── portfolio_linkage.py        # 组合联动分析器
└── api/v1/endpoints/
    └── enhanced_analysis.py        # API 聚合端点
```

---

### 3.2 催化剂聚合器实现

**文件：** `backend/app/services/catalyst_aggregator.py`

#### 数据源策略

| 数据类型 | 来源 | 验证状态 |
|---------|------|---------|
| 财报日期 | Yahoo Finance API | verified=true |
| FOMC 会议 | 硬编码日历 | verified=true |
| 产品发布会 | Agent 搜索 | verified=false |

#### 核心逻辑

```python
class CatalystAggregator:
    """催化剂聚合器"""
    
    async def fetch_catalysts(self, ticker: str, days_ahead: int = 30) -> List[Dict]:
        # 1. 财报日期（Yahoo Finance）
        earnings = await self._fetch_earnings_dates(ticker)
        
        # 2. FOMC 会议（硬编码）
        fomc = await self._fetch_fomc_dates(days_ahead)
        
        # 3. 产品发布会（Agent 搜索）
        events = await self._search_product_events(ticker, days_ahead)
        
        # 4. 合并排序
        catalysts = earnings + fomc + events
        catalysts.sort(key=lambda x: x["date"])
        
        return catalysts
```

#### Agent 搜索部分（核心）

```python
async def _search_product_events(self, ticker: str, days_ahead: int) -> List[Dict]:
    """使用 Agent 搜索产品发布会等非结构化事件"""
    
    # Prompt 设计要点：
    # 1. 明确搜索范围
    # 2. 要求标注来源
    # 3. 要求返回 JSON
    # 4. 强调不要编造
    
    prompt = f"""
请搜索 {ticker} 相关公司未来{days_ahead}天内的重大活动：

搜索范围：
1. 产品发布会、开发者大会
2. 重要合作伙伴公告
3. 监管听证会

输出要求：
- 只返回有明确日期的事件
- 每条必须标注信息来源
- 找不到可靠信息就返回空列表
- 不要编造日期

JSON 格式：[{{"event": "...", "date": "...", "source": "...", "impact": "..."}}]
"""
    
    # 调用 AI（使用带搜索能力的 Provider）
    response = await call_provider(...)
    events = parse_json(response)
    
    # 标记为未验证
    for event in events:
        event["verified"] = False
        event["source_type"] = "agent_search"
    
    return events
```

---

### 3.3 关键假设生成器实现

**文件：** `backend/app/services/assumption_generator.py`

#### 核心原则

```
AI 只负责格式化文字，不生成数据
所有数值必须来自真实市场数据
```

#### 规则引擎逻辑

```python
class AssumptionGenerator:
    """关键假设生成器"""
    
    async def generate(self, ticker: str, market_data: dict, analysis: dict) -> List[Dict]:
        assumptions = []
        
        # 规则 1: 均线支撑假设（有数据才生成）
        if market_data.get("ma_20"):
            distance = 计算距离百分比()
            assumptions.append({
                "assumption": "20 日均线不被有效跌破",
                "trigger": f"收盘价连续 2 日低于 ${ma_20:.2f}",
                "consequence": "视为趋势转弱信号",
                "current_status": f"当前距离 {distance:.1f}%",
                "risk_level": "核心假设" if abs(distance) < 5 else "辅助假设",
            })
        
        # 规则 2: 止损位假设
        if analysis and analysis.get("stop_loss_price"):
            assumptions.append({...})
        
        # 规则 3: VIX 宏观假设（仅当 VIX > 25）
        if market_data.get("vix", 0) > 25:
            assumptions.append({...})
        
        return assumptions
```

---

### 3.4 组合联动分析器实现

**文件：** `backend/app/services/portfolio_linkage.py`

#### 核心计算逻辑

```python
class PortfolioLinkageAnalyzer:
    """组合联动分析器"""
    
    async def analyze(self, db, user_id, ticker, new_quantity, current_price):
        # 1. 获取当前持仓
        portfolio = await self._get_portfolio(db, user_id)
        
        # 2. 计算当前总市值
        current_total = sum(p.market_value for p in portfolio)
        
        # 3. 计算当前行业敞口
        sector_map = self._calculate_sector_exposure(portfolio)
        
        # 4. 计算加仓后的变化
        new_value = new_quantity * current_price
        new_total = current_total + new_value
        sector_exposure = self._calculate_new_exposure(sector_map, new_value, new_total)
        
        # 5. 生成警告
        warnings = []
        for sector, exposure in sector_exposure.items():
            if exposure["after"] > 40:
                warnings.append(f"{sector}敞口超过建议上限 40%")
        
        # 6. 计算 Beta 变化
        beta_change = self._calculate_beta_change(portfolio, new_value)
        
        return {
            "sector_exposure": sector_exposure,
            "beta_change": beta_change,
            "warnings": warnings,
            "recommended_max_position": self._recommend_max_position(sector_exposure),
        }
```

---

### 3.5 API 聚合端点实现

**文件：** `backend/app/api/v1/endpoints/enhanced_analysis.py`

#### 端点设计

```python
@router.get("/{ticker}/enhanced")
async def get_enhanced_analysis(
    ticker: str,
    quantity: float = None,  # 可选：要加仓的数量
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取增强型 AI 分析"""
    
    # 1. 获取基础 AI 分析（现有服务）
    verdict = await GetLatestAnalysisUseCase(db, current_user).execute(ticker=ticker)
    
    # 2. 获取市场数据
    market_data = await MarketDataService.get_data(ticker, db)
    
    # 3. 生成关键假设
    assumptions = await assumption_generator.generate(ticker, market_data, verdict)
    
    # 4. 获取催化剂
    catalysts = await catalyst_aggregator.fetch_catalysts(ticker)
    
    # 5. 组合联动（仅当传了 quantity 时）
    linkage = None
    if quantity and quantity > 0:
        linkage = await portfolio_linkage_analyzer.analyze(db, current_user.id, ticker, quantity, market_data["current_price"])
    
    # 6. 统一返回
    return {
        "verdict": verdict,
        "assumptions": assumptions,
        "catalysts": catalysts,
        "linkage": linkage,
        "_metadata": {
            "assumptions_verified": all(a.get("_verified") for a in assumptions),
            "catalysts_verified_count": sum(1 for c in catalysts if c.get("verified")),
        },
    }
```

---

## 第四部分：输出格式规范

### 4.1 统一响应结构

```json
{
    "verdict": {...},
    "assumptions": [...],
    "catalysts": [...],
    "linkage": {...},
    "_metadata": {...}
}
```

### 4.2 通用字段说明

**所有催化剂事件的统一格式：**

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `date` | string | 事件日期 (ISO 8601) | `"2026-04-26"` |
| `event` | string | 事件名称 | `"Q1 2026 财报"` |
| `type` | string | 事件类型 | `"earnings"` |
| `impact` | string | 影响等级 | `"高"/"中"/"低"` |
| `verified` | boolean | 是否已验证 | `true`/`false` |
| `source` | string | 数据来源 | `"yfinance"` |

**关键假设的统一格式：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | integer | 假设序号 |
| `assumption` | string | 假设内容 |
| `trigger` | string | 触发条件 |
| `consequence` | string | 后果说明 |
| `current_status` | string | 当前状态 |
| `risk_level` | string | 风险等级 |
| `_verified` | boolean | 是否基于真实数据 |

---

### 4.3 事件类型枚举

```python
VALID_EVENT_TYPES = {
    "earnings": "财报发布",
    "macro": "宏观事件",
    "company_event": "公司活动",
    "analyst": "分析师动向",
    "liquidity": "流动性事件",
}
```

---

### 4.4 验证状态说明

| verified | 含义 | 前端如何处理 |
|----------|------|-------------|
| `true` | 来自可信源（API、官方日历） | 直接显示，无特殊标记 |
| `false` | 来自 Agent 搜索 | 显示"（需验证）"标签 |

---

## 第五部分：前端组件设计

### 5.1 组件结构

```
frontend/components/features/
├── VerdictCard.tsx           # 判研卡（复用现有 AIVerdict）
├── KeyAssumptions.tsx        # 关键假设断点（新建）
├── CatalystTimeline.tsx      # 催化剂时间轴（新建）
└── PortfolioLinkage.tsx      # 组合联动视角（新建）
```

---

### 5.2 关键假设组件

**核心 Props：**
```typescript
interface KeyAssumptionsProps {
    assumptions: Array<{
        id: number;
        assumption: string;
        trigger: string;
        consequence: string;
        current_status: string;
        risk_level: "核心假设" | "辅助假设";
    }>;
}
```

**设计要点：**
- 每条假设显示序号圆形图标
- 风险等级用颜色区分（核心=红色，辅助=黄色）
- 右侧显示"距突破"数值

---

### 5.3 催化剂时间轴组件

**核心 Props：**
```typescript
interface CatalystTimelineProps {
    catalysts: Array<{
        date: string;
        event: string;
        type: "earnings" | "macro" | "company_event";
        impact: "高" | "中" | "低";
        verified: boolean;
        days_away?: number;
    }>;
}
```

**设计要点：**
- 垂直时间轴布局
- 圆点颜色区分事件类型
- 倒计时数字根据紧急程度变色（≤5 天红色，≤15 天黄色）
- 未验证事件显示"（需验证）"标签

---

## 第六部分：开发时间估算

| 任务 | 预计时间 | 说明 |
|------|---------|------|
| **后端** | | |
| catalyst_aggregator.py | 0.5 天 | Yahoo+FOMC 简单，Agent 搜索需调试 |
| assumption_generator.py | 0.5 天 | 规则引擎逻辑 |
| portfolio_linkage.py | 0.5 天 | 数据库计算 |
| enhanced_analysis.py | 0.5 天 | API 聚合 |
| **前端** | | |
| KeyAssumptions.tsx | 0.5 天 | 列表组件 |
| CatalystTimeline.tsx | 0.5 天 | 时间轴组件 |
| PortfolioLinkage.tsx | 0.5 天 | 图表组件 |
| **联调测试** | 0.5 天 | 接口对接 |
| **总计** | **3.5 天** | |

---

## 第七部分：依赖安装

```bash
# 后端依赖
cd backend
pip install yfinance

# 前端依赖（如果还没有）
cd frontend
npm install clsx
```

---

## 第八部分：测试步骤

### 8.1 测试催化剂接口

```bash
curl http://localhost:8000/api/v1/enhanced-analysis/GOOGL/enhanced \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**检查点：**
- 财报日期是否准确
- FOMC 日期是否在硬编码列表中
- Agent 搜索的事件是否标注 `verified: false`

### 8.2 测试关键假设接口

**检查点：**
- 所有数值与行情数据一致
- AI 没有篡改输入数据
- 缺失数据时不生成对应假设

---

## 第九部分：常见问题

### Q1: Agent 搜索不到催化剂事件怎么办？

**A:** 返回空数组即可，前端不显示该模块。不要编造。

---

### Q2: 如何验证 Agent 搜索的结果？

**A:** 给每个结果加 `verified: false` 标记，前端显示"（需验证）"提示。用户可自行判断。

---

### Q3: 历史数据不足怎么办？

**A:** 暂时不做历史信号模块，等数据积累到 3 个月以上再考虑。

---

### Q4: Agent 调用失败如何处理？

**A:** 静默失败，返回空数组或 null。该模块前端不显示即可。

---

## 第十部分：总结

### 10.1 架构选择

| 场景 | 架构 | 原因 |
|------|------|------|
| 财报日期 | 直接 API 调用 | 准确、简单 |
| FOMC 日期 | 硬编码 | 100% 准确 |
| 产品发布会 | Agent 搜索 | 非结构化，需要灵活性 |
| 关键假设 | 规则引擎 + AI 格式化 | 数据必须真实，文字可以润色 |
| 组合联动 | 数据库计算 | 纯计算，无需 AI |

---

### 10.2 核心原则

```
1. 所有数据必须有来源标记
2. 可信源标记 verified=true，Agent 搜索标记 verified=false
3. AI 只格式化，不生成数值
4. 前端根据 verified 状态显示不同样式
```

---

### 10.3 任务拆解口诀

```
一看数据类型 → 结构化 or 非结构化
二选合适工具 → API or Agent
三定输出格式 → JSON + 来源标记
四做结果验证 → 可信源直接信，Agent 搜索需标注
```
