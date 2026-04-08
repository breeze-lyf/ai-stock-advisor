# AI 股票顾问系统 - Phase 2 实施计划

> **Phase 2 目标**: 完成所有待实现功能，打造专业级投资平台
> **实施日期**: 2026-04-07

---

## 一、功能清单与优先级

### P0 - 核心功能（高优先级）

| 功能 | 描述 | 预计工作量 |
|------|------|------------|
| 多股票列表支持 | 每个用户可创建多个自定义股票列表 | 4 小时 |
| WebSocket 实时推送 | 实时股价更新、AI 分析完成通知 | 6 小时 |
| 选股器 | 预设策略 + 自定义筛选 | 6 小时 |

### P1 - 重要功能（中优先级）

| 功能 | 描述 | 预计工作量 |
|------|------|------------|
| 投资组合风险敞口分析 | 行业/地域/市值风格暴露 | 4 小时 |
| 相关性热力图 | 持仓股票相关系数可视化 | 3 小时 |
| 智能分级推送 | P0/P1/P2 三级推送体系 | 3 小时 |
| 财经日历 | 宏观经济事件 + 财报季 | 4 小时 |

### P2 - 增强功能（低优先级）

| 功能 | 描述 | 预计工作量 |
|------|------|------------|
| 再平衡建议引擎 | 检测偏离权重，生成调仓建议 | 4 小时 |
| 业绩归因分析 | 个股选择/行业配置/市场时机贡献 | 4 小时 |
| 浏览器推送 | Web Push API 集成 | 2 小时 |
| 静默时段设置 | 免打扰时间配置 | 1 小时 |

---

## 二、技术架构设计

### 2.1 多股票列表支持

**数据模型**:
```python
class StockList(Base):
    id: str                    # UUID
    user_id: str               # 外键
    name: str                  # 列表名称
    description: str           # 描述
    is_default: bool           # 是否默认列表
    stocks: List[StockListItem]

class StockListItem(Base):
    id: str
    list_id: str
    ticker: str
    added_at: datetime
    notes: str
```

**API 端点**:
- `GET /api/v1/portfolio/lists` - 获取用户所有列表
- `POST /api/v1/portfolio/lists` - 创建新列表
- `PUT /api/v1/portfolio/lists/{id}` - 更新列表
- `DELETE /api/v1/portfolio/lists/{id}` - 删除列表
- `POST /api/v1/portfolio/lists/{id}/stocks` - 添加股票
- `DELETE /api/v1/portfolio/lists/{id}/stocks/{ticker}` - 移除股票

### 2.2 WebSocket 实时推送

**架构**:
```
前端连接 → WebSocket Manager → 订阅管理 → 消息推送
                ↓
          Redis Pub/Sub (跨实例通信)
```

**消息类型**:
- `price_update` - 股价更新
- `analysis_complete` - AI 分析完成
- `alert_triggered` - 预警触发
- `system_notification` - 系统通知

### 2.3 选股器

**筛选条件**:
- 技术指标：RSI, MACD, MA, BB
- 基本面：PE, PB, ROE, 营收增速
- 资金面：北向资金，主力净流入

**预设策略**:
- 低估值策略 (PE<15, PB<2)
- 成长策略 (营收增速>20%)
- 动量策略 (20 日新高)
- 高股息策略 (股息率>5%)

### 2.4 投资组合 2.0

**风险敞口**:
- 行业集中度
- 地域集中度
- 市值风格暴露

**再平衡建议**:
- 检测偏离权重
- 生成调仓建议
- 估算交易成本

---

## 三、实施顺序

### 第一阶段：数据层（Day 1）
1. 多股票列表数据模型 + 迁移
2. 投资组合分析数据模型
3. 财经日历数据模型

### 第二阶段：后端服务（Day 2-3）
1. 选股器服务
2. WebSocket 服务
3. 投资组合分析服务
4. 财经日历服务

### 第三阶段：前端实现（Day 4-5）
1. 多股票列表 UI
2. 选股器 UI
3. 投资组合分析 UI
4. 财经日历 UI

### 第四阶段：测试与优化（Day 6）
1. 集成测试
2. 性能优化
3. 文档完善

---

## 四、成功指标

| 指标 | 目标值 |
|------|--------|
| WebSocket 连接成功率 | >99% |
| 选股器响应时间 | <2s |
| 投资组合分析准确率 | >95% |
| 用户满意度 | >4.5/5 |

---

© 2026 AI Smart Investment Advisor
