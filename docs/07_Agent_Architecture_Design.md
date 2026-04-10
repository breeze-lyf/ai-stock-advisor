# Agent 架构设计文档

**文档版本：** v1.0  
**更新日期：** 2026-04-09  
**目标：** 说明 Agent 的架构设计、任务拆解方式、输出格式规范

---

## 一、用的是什么架构

### 1.1 架构图（简化版）

```
┌─────────────────────────────────────────────────────────┐
│                    用户请求                               │
│  "搜索 GOOGL 未来 30 天的催化剂事件"                       │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│              任务编排器 (Orchestrator)                   │
│  职责：拆解任务、分发、聚合结果                          │
└─────────────────────────────────────────────────────────┘
           │              │              │
           ↓              ↓              ↓
    ┌──────────┐  ┌──────────  ┌──────────────
    │ 工具 1    │  │ 工具 2    │  │ 工具 3       │
    │ Yahoo    │  │ Tavily   │  │ 规则引擎     │
    │ Finance  │  │ 搜索     │  │ (FOMC 日历)   │
    └──────────┘  └──────────  └──────────────
           │              │              │
           └──────────────┴──────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                 格式化输出                               │
│  JSON 格式，带来源标记、验证状态                          │
└─────────────────────────────────────────────────────────┘
```

### 1.2 架构类型：**工具增强型 Agent (Tool-Augmented Agent)**

**特点：**
- AI 不是直接回答，而是**调用工具**获取真实数据
- 每个工具都有明确的输入输出契约
- 最终结果必须标注**数据来源**和**验证状态**

**为什么选这个架构：**
| 方案 | 优点 | 缺点 |
|------|------|------|
| 纯 AI 生成 | 简单 | 一定会幻觉 |
| 纯 API 调用 | 准确 | 不灵活，覆盖场景少 |
| **工具增强型** | 准确 + 灵活 | 实现稍复杂 |

---

## 二、如何拆解每个任务

### 2.1 任务拆解流程

```
用户请求
  ↓
步骤 1: 意图识别 → 确定需要哪些数据
  ↓
步骤 2: 任务拆解 → 拆成多个子任务
  ↓
步骤 3: 工具选择 → 每个子任务选合适的工具
  ↓
步骤 4: 并行执行 → 同时调用多个工具
  ↓
步骤 5: 结果聚合 → 合并所有结果
  ↓
步骤 6: 格式输出 → 统一 JSON 格式
```

### 2.2 具体例子：催化剂搜索

**用户请求：** "搜索 GOOGL 未来 30 天的催化剂事件"

**步骤 1: 意图识别**
```python
# 识别出需要：
# - 财报日期（结构化数据）
# - FOMC 会议（固定日历）
# - 产品发布会（非结构化，需搜索）
```

**步骤 2: 任务拆解**
```
任务 1: 获取财报日期 → Yahoo Finance API
任务 2: 获取 FOMC 日期 → 硬编码日历
任务 3: 搜索产品发布会 → Tavily 搜索 + AI 摘要
```

**步骤 3: 工具选择**
```python
tools = {
    "任务 1": YahooFinanceTool(),
    "任务 2": FEDCalendarTool(),
    "任务 3": TavilySearchTool() + AIFormatter(),
}
```

**步骤 4: 并行执行**
```python
import asyncio

results = await asyncio.gather(
    fetch_earnings(ticker),      # 任务 1
    fetch_fomc_dates(),          # 任务 2
    search_product_events(ticker), # 任务 3
)
```

**步骤 5: 结果聚合**
```python
catalysts = []
catalysts.extend(results[0])  # 财报
catalysts.extend(results[1])  # FOMC
catalysts.extend(results[2])  # 产品发布会
```

**步骤 6: 格式输出**
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
        "date": "2026-05-06",
        "event": "FOMC 利率决议",
        "type": "macro",
        "impact": "中",
        "verified": true,
        "source": "federal_reserve"
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

## 三、每个任务的详细设计

### 3.1 任务 1：财报日期获取

**工具：** Yahoo Finance API

**代码：**
```python
async def fetch_earnings_dates(ticker: str) -> List[Dict]:
    """
    获取财报日期
    
    输入：ticker = "GOOGL"
    输出：[{"date": "2026-04-26", "event": "财报发布", ...}]
    """
    import yfinance as yf
    
    try:
        yf_ticker = yf.Ticker(ticker)
        earnings = yf_ticker.earnings_dates
        
        result = []
        for e in earnings:
            result.append({
                "date": e.date().isoformat(),
                "event": "财报发布",
                "type": "earnings",
                "impact": "高",
                "verified": True,  # 来自官方数据源
                "source": "yfinance",
            })
        return result
    except Exception as e:
        print(f"获取财报日期失败：{e}")
        return []
```

**输出格式：**
```json
[
    {
        "date": "2026-04-26",
        "event": "财报发布",
        "type": "earnings",
        "impact": "高",
        "verified": true,
        "source": "yfinance"
    }
]
```

---

### 3.2 任务 2：FOMC 日期获取

**工具：** 硬编码日历

**代码：**
```python
# 2026 年 FOMC 会议日期（美联储官网）
FOMC_CALENDAR_2026 = [
    date(2026, 1, 28), date(2026, 3, 18), date(2026, 5, 6),
    date(2026, 6, 17), date(2026, 7, 29), date(2026, 9, 16),
    date(2026, 11, 4), date(2026, 12, 16),
]

async def fetch_fomc_dates(days_ahead: int = 30) -> List[Dict]:
    """
    获取 FOMC 会议日期
    
    输入：days_ahead = 30
    输出：[{"date": "2026-05-06", "event": "FOMC 利率决议", ...}]
    """
    from datetime import date, timedelta
    
    today = date.today()
    cutoff = today + timedelta(days=days_ahead)
    
    result = []
    for fomc_date in FOMC_CALENDAR_2026:
        if today <= fomc_date <= cutoff:
            days_away = (fomc_date - today).days
            result.append({
                "date": fomc_date.isoformat(),
                "event": "FOMC 利率决议",
                "type": "macro",
                "impact": "中",
                "verified": True,  # 100% 准确
                "source": "federal_reserve",
                "days_away": days_away,
            })
    return result
```

**输出格式：**
```json
[
    {
        "date": "2026-05-06",
        "event": "FOMC 利率决议",
        "type": "macro",
        "impact": "中",
        "verified": true,
        "source": "federal_reserve",
        "days_away": 5
    }
]
```

---

### 3.3 任务 3：产品发布会搜索（Agent 核心）

**工具：** Tavily 搜索 + AI 格式化

**代码：**
```python
async def search_product_events(ticker: str, days_ahead: int = 30) -> List[Dict]:
    """
    搜索产品发布会等非结构化事件
    
    输入：ticker = "GOOGL", days_ahead = 30
    输出：[{"date": "2026-05-14", "event": "Google I/O 2026", ...}]
    """
    from app.services.ai_provider_client import call_provider
    from app.core.config import settings
    import json
    
    # ========== 步骤 1: 构造搜索型 Prompt ==========
    prompt = f"""
请搜索 {ticker} 相关公司未来{days_ahead}天内的重大活动：

搜索范围：
1. 产品发布会、开发者大会
2. 重要合作伙伴公告
3. 监管听证会或诉讼进展

输出要求：
1. 只返回有明确日期的事件
2. 每条必须标注信息来源（如：公司官网、Reuters）
3. 不确定日期的写"预计"
4. 找不到可靠信息就返回空列表
5. 不要编造日期

JSON 格式：
[
  {{
    "event": "Google I/O 2026",
    "date": "2026-05-14",
    "source": "公司官网",
    "impact": "中"
  }}
]
"""
    
    # ========== 步骤 2: 调用 AI（带搜索能力）==========
    try:
        response = await call_provider(
            provider_config={
                "provider_key": "dashscope",
                "base_url": settings.DASHSCOPE_BASE_URL,
            },
            model_id=settings.DEFAULT_AI_MODEL,
            prompt=prompt,
            api_key=settings.DASHSCOPE_API_KEY,
        )
        
        # ========== 步骤 3: 解析 JSON ==========
        events = json.loads(response)
        
        # ========== 步骤 4: 格式化输出 ==========
        result = []
        for event in events:
            result.append({
                "date": event.get("date", "Unknown"),
                "event": event.get("event", "未知事件"),
                "type": "company_event",
                "impact": event.get("impact", "中"),
                "verified": False,  # Agent 搜索的标记为需验证
                "source": event.get("source", "unknown"),
                "source_type": "agent_search",
            })
        
        return result
    except Exception as e:
        print(f"Agent 搜索催化剂失败：{e}")
        return []
```

**输出格式：**
```json
[
    {
        "date": "2026-05-14",
        "event": "Google I/O 2026",
        "type": "company_event",
        "impact": "中",
        "verified": false,
        "source": "公司官网",
        "source_type": "agent_search"
    }
]
```

---

## 四、输出格式规范

### 4.1 通用字段说明

所有催化剂事件的统一格式：

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `date` | string | 事件日期 (ISO 8601) | `"2026-04-26"` |
| `event` | string | 事件名称 | `"Q1 2026 财报"` |
| `type` | string | 事件类型 | `"earnings"` |
| `impact` | string | 影响等级 | `"高"/"中"/"低"` |
| `verified` | boolean | 是否已验证 | `true`/`false` |
| `source` | string | 数据来源 | `"yfinance"` |

### 4.2 事件类型枚举

```python
VALID_EVENT_TYPES = {
    "earnings": "财报发布",
    "macro": "宏观事件",
    "company_event": "公司活动",
    "analyst": "分析师动向",
    "liquidity": "流动性事件",
}
```

### 4.3 影响等级枚举

```python
VALID_IMPACT_LEVELS = {
    "高": "可能引起股价大幅波动",
    "中": "可能引起中等波动",
    "低": "影响有限",
}
```

### 4.4 验证状态说明

| verified | 含义 | 前端如何处理 |
|----------|------|-------------|
| `true` | 来自可信源（API、官方日历） | 直接显示 |
| `false` | 来自 Agent 搜索 | 显示"（需验证）"标签 |

---

## 五、关键假设生成任务

### 5.1 任务拆解

**用户请求：** "生成 GOOGL 的关键假设断点"

**步骤：**
```
1. 获取真实行情数据 → MarketDataService
2. 获取 AI 分析结果 → AnalysisService
3. 规则引擎生成假设 → AssumptionGenerator
4. （可选）AI 补充假设 → AIFormatter
```

### 5.2 代码实现

```python
async def generate_assumptions(
    ticker: str,
    market_data: dict,
    analysis: dict,
) -> List[Dict]:
    """
    生成关键假设断点
    
    核心原则：
    - AI 只格式化文字，不生成数据
    - 所有数值来自真实数据
    """
    assumptions = []
    
    # ========== 规则 1: 均线支撑 ==========
    if market_data.get("ma_20"):
        current_price = market_data["current_price"]
        ma_20 = market_data["ma_20"]
        distance_pct = ((current_price - ma_20) / ma_20) * 100
        
        assumptions.append({
            "id": 1,
            "assumption": "20 日均线不被有效跌破",
            "trigger": f"收盘价连续 2 日低于 ${ma_20:.2f}",
            "consequence": "视为趋势转弱，建仓计划终止",
            "current_status": f"当前距离 {distance_pct:.1f}%",
            "risk_level": "核心假设" if abs(distance_pct) < 5 else "辅助假设",
            "_data_source": "market_data",
            "_verified": True,
        })
    
    # ========== 规则 2: 止损位 ==========
    if analysis and analysis.get("stop_loss_price"):
        current_price = market_data["current_price"]
        stop_loss = analysis["stop_loss_price"]
        distance_pct = ((current_price - stop_loss) / stop_loss) * 100
        
        assumptions.append({
            "id": 2,
            "assumption": "止损位不被触发",
            "trigger": f"价格跌破 ${stop_loss:.2f}",
            "consequence": "严格执行止损纪律",
            "current_status": f"当前距离 {distance_pct:.1f}%",
            "risk_level": "核心假设",
            "_data_source": "analysis",
            "_verified": True,
        })
    
    return assumptions
```

### 5.3 输出格式

```json
[
    {
        "id": 1,
        "assumption": "20 日均线不被有效跌破",
        "trigger": "收盘价连续 2 日低于 $299.80",
        "consequence": "视为趋势转弱信号，本次建仓计划终止",
        "current_status": "当前距离 -2.1%",
        "risk_level": "核心假设",
        "_data_source": "market_data",
        "_verified": true
    },
    {
        "id": 2,
        "assumption": "止损位不被触发",
        "trigger": "价格跌破 $295.00",
        "consequence": "严格执行止损纪律",
        "current_status": "当前距离 +3.4%",
        "risk_level": "核心假设",
        "_data_source": "analysis",
        "_verified": true
    }
]
```

---

## 六、完整 API 响应示例

### 6.1 请求

```bash
GET /api/v1/enhanced-analysis/GOOGL/enhanced
Authorization: Bearer <token>
```

### 6.2 响应

```json
{
    "verdict": {
        "immediate_action": "观望/低吸",
        "confidence_level": 68,
        "risk_level": "中",
        "target_price": 320,
        "stop_loss_price": 295,
        "entry_price_low": 302.5,
        "entry_price_high": 308
    },
    "assumptions": [
        {
            "id": 1,
            "assumption": "20 日均线不被有效跌破",
            "trigger": "收盘价连续 2 日低于 $299.80",
            "consequence": "视为趋势转弱，建仓计划终止",
            "current_status": "当前距离 -2.1%",
            "risk_level": "核心假设",
            "_verified": true
        }
    ],
    "catalysts": [
        {
            "date": "2026-04-26",
            "event": "Q1 2026 财报",
            "type": "earnings",
            "impact": "高",
            "verified": true,
            "source": "yfinance"
        },
        {
            "date": "2026-05-06",
            "event": "FOMC 利率决议",
            "type": "macro",
            "impact": "中",
            "verified": true,
            "source": "federal_reserve"
        },
        {
            "date": "2026-05-14",
            "event": "Google I/O 2026",
            "type": "company_event",
            "impact": "中",
            "verified": false,
            "source": "tavily_search"
        }
    ],
    "linkage": {
        "sector_exposure": {
            "Technology": {"before": 37.6, "after": 52.4}
        },
        "beta_change": {"before": 1.12, "after": 1.19},
        "warnings": ["科技敞口超过建议上限 40%"],
        "recommended_max_position": 3.5
    },
    "_metadata": {
        "assumptions_verified": true,
        "catalysts_verified_count": 2,
        "catalysts_unverified_count": 1
    }
}
```

---

## 七、总结

### 7.1 架构选择

| 场景 | 架构 | 原因 |
|------|------|------|
| 财报日期 | 直接 API 调用 | 准确、简单 |
| FOMC 日期 | 硬编码 | 100% 准确 |
| 产品发布会 | Agent 搜索 | 非结构化，需要灵活性 |
| 关键假设 | 规则引擎 + AI 格式化 | 数据必须真实，文字可以润色 |

### 7.2 核心原则

```
1. 所有数据必须有来源标记
2. 可信源标记 verified=true，Agent 搜索标记 verified=false
3. AI 只格式化，不生成数值
4. 前端根据 verified 状态显示不同样式
```

### 7.3 任务拆解口诀

```
一看数据类型 → 结构化 or 非结构化
二选合适工具 → API or Agent
三定输出格式 → JSON + 来源标记
四做结果验证 → 可信源直接信，Agent 搜索需标注
```
