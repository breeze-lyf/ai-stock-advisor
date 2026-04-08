# AI 股票顾问系统 - 产品优化计划

> 文档创建时间：2026-04-07
> 目标：从产品角度全面优化系统，提升用户体验、功能完整性和商业价值

---

## 一、当前系统分析

### 1.1 核心功能盘点

| 模块 | 功能 | 状态 | 问题/不足 |
|------|------|------|-----------|
| 用户认证 | 登录/注册/Token 管理 | ✅ 已实现 | 缺少邮箱验证、密码强度要求低、无两步验证 |
| 个股分析 | AI 技术面 + 基本面分析 | ✅ 已实现 | 分析维度可擴展、缺少历史信号追踪 |
| 投资组合 | 持仓管理 + 组合分析 | ✅ 已实现 | 缺少自动 rebalance 建议、风险敞口可视化不足 |
| 宏观雷达 | 全球宏观热点扫描 | ✅ 已实现 | 推送频率固定、缺少用户自定义主题 |
| 通知系统 | 飞书 webhook 推送 | ✅ 已实现 | 渠道单一、缺少 APP 推送/邮件 |
| 模拟交易 | 纸面交易回测 | ✅ 已实现 | 功能基础、缺少策略回测 |
| AI 配置 | 多模型支持 + BYOK | ✅ 已实现 | 配置入口深、缺少使用统计 |

### 1.2 技术架构评估

**优势：**
- 前后端分离清晰（Next.js 16 + FastAPI）
- 数据库设计合理，支持异步操作
- AI 服务支持多供应商故障转移
- 容器化部署，支持 Docker Compose

**待改进：**
- 缺少实时 WebSocket 推送（目前靠轮询）
- 前端缓存策略可优化
- 缺少 APM 监控和告警
- 测试覆盖率不足

### 1.3 用户体验问题

1. **首次用户体验差**：注册后无引导，不知道如何使用
2. **信息密度过高**：首页堆砌太多数据，新手难以理解
3. **缺少上下文帮助**：专业术语无解释
4. **移动端功能阉割**：Taro 移动端功能不完整
5. **无暗色模式切换**：虽然有 ThemeProvider，但设置页入口深

---

## 二、产品优化路线图

### 2.1 用户体验优化（UX Improvements）

#### 2.1.1 新用户引导流程
**目标**：降低学习成本，提升留存率

**功能设计：**
1. **欢迎向导（3 步）**：
   - Step 1: 选择投资偏好（保守/稳健/激进）
   - Step 2: 选择关注市场（A 股/港股/美股）
   - Step 3: 设置通知偏好（飞书/邮件/免打扰）

2. **交互式教程**：
   - 首次访问个股分析页时，高亮展示关键指标含义
   - 首次查看 AI 分析时，解释如何解读"决策坐标系"

3. **空状态优化**：
   - 无持仓时显示"如何开始"引导
   - 无 AI 分析时显示"添加股票"快捷入口

**实现文件：**
- `frontend/app/onboarding/page.tsx` (新增)
- `frontend/components/features/OnboardingWizard.tsx` (新增)
- `backend/app/api/v1/endpoints/user_preferences.py` (新增)

---

#### 2.1.2 仪表盘个性化
**目标**：让用户自定义关注的核心指标

**功能设计：**
1. **可拖拽的卡片布局**：用户可 reorder 关注模块
2. **指标卡片库**：提供 10+ 种指标卡片选择
3. **快速视图切换**：
   - "简洁视图"：只显示核心数据
   - "专业视图"：显示全部技术指标
   - "对比视图"：多股票并列对比

**实现文件：**
- `frontend/components/features/DashboardLayout.tsx` (新增)
- `frontend/lib/layoutStorage.ts` (新增)
- `backend/app/models/user_dashboard_config.py` (新增)

---

### 2.2 核心功能增强（Core Features）

#### 2.2.1 AI 分析系统升级
**目标**：提升 AI 分析的专业性和可操作性

**功能设计：**
1. **多时间框架分析**：
   - 短线视角（1-5 日）
   - 中线视角（1-4 周）
   - 长线视角（3-12 月）

2. **情景分析（Scenario Analysis）**：
   - 乐观情景：目标价 +20%
   - 基准情景：目标价 +5%
   - 悲观情景：目标价 -15%

3. **风险因子分解**：
   - 市场风险（β系数）
   - 行业风险（板块轮动）
   - 个股风险（财务/诉讼/高管变动）

4. **信号回溯系统**：
   - 记录每次 AI 建议的发布价格
   - 实时追踪"如果 follow 建议"的盈亏
   - 生成月度/季度胜率报告

**实现文件：**
- `backend/app/services/ai_analysis_enhanced.py` (新增)
- `backend/app/models/ai_signal_history.py` (新增)
- `frontend/components/features/stock-detail/ScenarioAnalysis.tsx` (新增)
- `frontend/features/analysis/api.ts` (增强)

---

#### 2.2.2 投资组合管理 2.0
**目标**：从"持仓展示"升级为"智能投顾"

**功能设计：**
1. **风险敞口分析**：
   - 行业集中度（饼图 + 警戒线）
   - 地域集中度（地图可视化）
   - 市值风格暴露（大盘/中盘/小盘）

2. **相关性热力图**：
   - 展示持仓股票之间的相关系数
   - 高相关性（>0.8）标红警示

3. **再平衡建议**：
   - 检测偏离目标权重的持仓
   - 生成调仓建议（买 X 股/卖 Y 股）
   - 估算交易成本和税费

4. **业绩归因**：
   - 个股选择贡献
   - 行业配置贡献
   - 市场时机贡献

**实现文件：**
- `backend/app/application/portfolio/risk_analytics.py` (新增)
- `backend/app/application/portfolio/rebalance_engine.py` (新增)
- `frontend/components/features/PortfolioRiskChart.tsx` (新增)
- `frontend/components/features/CorrelationHeatmap.tsx` (新增)

---

#### 2.2.3 通知系统升级
**目标**：打造多渠道、智能化的通知体系

**功能设计：**
1. **多渠道支持**：
   - 飞书（现有）
   - 邮件（新增）
   - 浏览器推送（新增）
   - 短信（可选，付费功能）

2. **智能分级推送**：
   | 级别 | 场景 | 渠道 | 频率限制 |
   |------|------|------|----------|
   | P0 | 止损触发、重大利空 | 全渠道 | 无限制 |
   | P1 | 目标价接近、加仓信号 | 飞书 + 邮件 | 5 条/日 |
   | P2 | 常规复盘、周报 | 邮件 | 1 条/日 |
   | P3 | 市场资讯、快讯 | 飞书 | 10 条/日 |

3. **静默时段**：用户设置免打扰时间（如 22:00-8:00）

4. **推送模板自定义**：
   - 简洁版：只包含核心数据
   - 详细版：包含完整分析逻辑

**实现文件：**
- `backend/app/services/notification_service_v2.py` (重构)
- `backend/app/services/email_service.py` (新增)
- `backend/app/models/notification_channel.py` (新增)
- `backend/app/models/notification_template.py` (新增)

---

### 2.3 新增功能模块（New Features）

#### 2.3.1 选股器（Stock Screener）
**目标**：帮助用户从全市场发现机会

**功能设计：**
1. **预设策略**：
   - 低估值策略（PE<15, PB<2）
   - 成长策略（营收增速>20%, 净利增速>30%）
   - 动量策略（20 日新高，MACD 金叉）
   - 高股息策略（股息率>5%，连续 3 年分红）

2. **自定义条件**：
   - 技术指标（MA/MACD/RSI/KDJ）
   - 基本面指标（PE/PB/ROE/毛利率）
   - 资金面指标（北向资金/主力净流入）

3. **结果可视化**：
   - 列表模式（支持排序/导出）
   - 卡片模式（缩略图 + 核心指标）

**实现文件：**
- `backend/app/api/v1/endpoints/screener.py` (新增)
- `backend/app/services/stock_screener.py` (新增)
- `frontend/app/screener/page.tsx` (新增)
- `frontend/components/features/StockScreener.tsx` (新增)

---

#### 2.3.2 财经日历（Economic Calendar）
**目标**：帮助用户预判市场波动

**功能设计：**
1. **事件类型**：
   - 央行议息会议（美联储/欧央行/日本央行/中国央行）
   - 通胀数据（CPI/PPI）
   - 就业数据（非农就业/失业率）
   - GDP 数据
   - 财报季（美股七大巨头财报日）

2. **影响程度标注**：
   - 🔴 高影响
   - 🟡 中影响
   - 🟢 低影响

3. **持仓关联**：
   - 自动高亮与用户持仓相关的事件
   - 推送"事件前瞻"和"事件解读"

**实现文件：**
- `backend/app/services/economic_calendar_fetcher.py` (新增)
- `backend/app/models/economic_event.py` (新增)
- `frontend/app/calendar/page.tsx` (新增)
- `frontend/components/features/EconomicCalendar.tsx` (新增)

---

#### 2.3.3 策略回测引擎（Strategy Backtester）
**目标**：让用户验证自己的投资想法

**功能设计：**
1. **策略定义**：
   - 入场条件（如：MA20 上穿 MA50）
   - 出场条件（如：亏损 10% 止损）
   - 仓位规则（如：每次买入 20%）

2. **回测参数**：
   - 回测区间（如：2020-01-01 至 2026-04-07）
   - 初始资金（如：100 万虚拟资金）
   - 手续费率（如：万分之 3）

3. **回测报告**：
   - 年化收益率
   - 最大回撤
   - 夏普比率
   - 胜率
   - 盈亏比
   - 权益曲线图

**实现文件：**
- `backend/app/services/backtester/engine.py` (新增)
- `backend/app/services/backtester/strategies.py` (新增)
- `backend/app/models/backtest_result.py` (新增)
- `frontend/app/backtest/page.tsx` (新增)
- `frontend/components/features/BacktestReport.tsx` (新增)

---

#### 2.3.4 投资者教育（Investment Academy）
**目标**：提升用户投资知识，增加粘性

**功能设计：**
1. **课程分类**：
   - 入门篇：股票基础、交易规则
   - 进阶篇：技术分析、基本面分析
   - 高级篇：期权策略、量化投资

2. **学习进度追踪**：
   - 完成课程获得积分
   - 积分可兑换 PRO 会员体验

3. **小测验**：
   - 每节课后 3-5 道选择题
   - 答对才能进入下一节

**实现文件：**
- `backend/app/api/v1/endpoints/academy.py` (新增)
- `backend/app/models/course.py` (新增)
- `frontend/app/learn/page.tsx` (新增)
- `frontend/components/features/CoursePlayer.tsx` (新增)

---

### 2.4 技术架构升级（Technical Improvements）

#### 2.4.1 WebSocket 实时推送
**目标**：减少轮询，提升实时性

**功能设计：**
1. **连接管理**：
   - 用户登录后建立 WebSocket 连接
   - 心跳检测（30s 一次）
   - 断线重连（指数退避）

2. **推送类型**：
   - 股价异动（涨跌幅>3%）
   - AI 信号生成完成
   - 飞书推送失败通知

**实现文件：**
- `backend/app/websocket/manager.py` (新增)
- `backend/app/websocket/routes.py` (新增)
- `frontend/lib/websocket.ts` (新增)
- `frontend/context/WebSocketContext.tsx` (新增)

---

#### 2.4.2 前端性能优化
**目标**：首屏加载时间<2s，交互响应<100ms

**优化措施：**
1. **代码分割**：按路由拆分 bundle
2. **图片优化**：WebP 格式 + lazy loading
3. **接口聚合**：GraphQL 或 batch requests
4. **骨架屏**：加载时显示占位 UI
5. **Service Worker**：离线缓存静态资源

**实现文件：**
- `frontend/next.config.ts` (优化)
- `frontend/lib/batchClient.ts` (新增)
- `frontend/components/ui/Skeleton.tsx` (新增)

---

#### 2.4.3 监控与告警
**目标**：问题发生 10 分钟内感知

**功能设计：**
1. **APM 指标采集**：
   - API 响应时间 P95/P99
   - 错误率（按端点）
   - 数据库慢查询

2. **业务指标监控**：
   - DAU/MAU
   - AI 调用成功率
   - 推送到达率

3. **告警渠道**：
   - 飞书机器人
   - 邮件
   - 短信（紧急情况）

**实现文件:**
- `backend/app/middleware/monitoring.py` (新增)
- `monitoring/prometheus/prometheus.yml` (新增)
- `monitoring/grafana/dashboards/` (新增 dashboard JSON)

---

### 2.5 商业化功能（Monetization）

#### 2.5.1 会员体系设计
**目标**：为 PRO 版本提供差异化价值

| 功能 | FREE | PRO (¥99/月) |
|------|------|--------------|
| 每日 AI 分析次数 | 3 次 | 无限 |
| 通知渠道 | 飞书 | 飞书 + 邮件 + 短信 |
| 选股器条件数 | 3 个 | 无限 |
| 回测历史长度 | 1 年 | 10 年 |
| 持仓股票数上限 | 10 只 | 50 只 |
| 数据刷新频率 | 15 分钟 | 实时 |
| 投资课程 | 基础篇 | 全部课程 |

**实现文件：**
- `backend/app/api/v1/endpoints/subscription.py` (新增)
- `backend/app/services/payment_service.py` (新增)
- `frontend/components/features/UpgradeModal.tsx` (新增)

---

## 三、实施优先级

### Phase 1（2026-04，高优先级）
1. 新用户引导流程
2. AI 分析系统升级（多时间框架 + 情景分析）
3. 信号回溯系统
4. WebSocket 实时推送
5. 通知系统升级（邮件渠道）

### Phase 2（2026-05，中优先级）
1. 投资组合管理 2.0（风险敞口 + 再平衡）
2. 选股器
3. 财经日历
4. 前端性能优化
5. 监控与告警

### Phase 3（2026-06，低优先级）
1. 策略回测引擎
2. 投资者教育
3. 仪表盘个性化
4. 会员体系
5. 移动端功能完善

---

## 四、成功指标

| 指标 | 当前值 | 目标值 | 测量方式 |
|------|--------|--------|----------|
| 日活跃用户 (DAU) | - | +50% | 后端登录日志 |
| 用户留存率 (D7) | - | >40% | 用户活跃追踪 |
| AI 分析使用率 | - | >70% | 功能点击统计 |
| 通知打开率 | - | >30% | 推送点击追踪 |
| 页面加载时间 | ~3s | <2s | Lighthouse |
| API 错误率 | - | <0.1% | 监控日志 |

---

## 五、变更记录

所有实现细节将记录在 `CHANGELOG_PRODUCT.md` 中。
