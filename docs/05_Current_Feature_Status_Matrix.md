# 05. 当前功能状态矩阵（研发/测试交付清单）

**文档版本：** V1.2
**更新时间：** 2026年5月4日
**适用对象：** 研发、测试、产品、运维

---

## 1. 使用说明

本清单用于回答三个问题：

1. 当前功能是否已经进入仓库主实现。
2. 功能是已完成、部分完成，还是仅有骨架。
3. 测试在提测时最少需要覆盖哪些路径。

状态定义：

- 已完成：主流程可稳定使用，具备基础异常处理。
- 部分完成：已存在页面、接口或数据结构，但生命周期、边界处理或联调尚未补齐。
- 骨架已入库：目录、路由、模型或迁移已出现，但尚不能视为可交付功能。
- 未开始：仓库中暂无明确实现。

---

## 2. 全局能力矩阵

| 功能域 | 子能力 | 状态 | 主要入口 | 后端支撑 | 测试优先级 |
|--------|--------|------|----------|----------|------------|
| 用户系统 | 注册/登录/鉴权 | 已完成 | Web 登录注册页、移动端登录注册页 | `/api/auth/*` | P0 |
| 用户系统 | 用户资料/偏好/安全设置 | 已完成 | Web 设置页、移动端设置页 | `/api/user/*`、`/api/user-profile/*`、`/api/user-preferences/*` | P0 |
| 持仓管理 | 持仓增删改查 | 已完成 | Web 首页/组合页、移动端首页/组合页 | `/api/portfolio/*` | P0 |
| 持仓管理 | 组合汇总视图 | 已完成 | Web `portfolio` 页、移动端概览 | `/api/portfolio/summary` | P0 |
| 持仓管理 | 股票搜索（A/H/US） | 已完成 | 搜索组件 | `application/portfolio/search_engine.py` | P0 |
| 行情数据 | A股/港股/美股行情拉取与缓存 | 已完成 | 首页与个股页自动展示 | `market_data*` 服务链路 + `market_providers/` | P0 |
| 行情数据 | StockCapsule（新闻/基本面摘要） | 部分完成 | 个股详情页摘要区 | `models/stock_capsule.py` + `application/analysis/generate_stock_capsule.py` | P1 |
| AI 个股诊断 | 单股分析报告 | 已完成 | 个股详情页 | `/api/analysis/{ticker}` + `application/analysis/analyze_stock.py` | P0 |
| AI 个股诊断 | 增强分析/多场景分析 | 部分完成 | Web 个股分析扩展区域 | `/api/enhanced-analysis/*` | P1 |
| AI 组合分析 | 组合级 AI 报告 | 已完成 | 组合页分析区 | `/api/analysis/portfolio` + `application/analysis/analyze_portfolio.py` | P1 |
| 宏观雷达 | 宏观主题与快讯 | 已完成 | 宏观页（Web/移动端） | `/api/macro/*` + `services/macro_service.py` + 定时任务 | P1 |
| 宏观雷达 | 全球异动雷达/雷达组合警报 | 已完成 | 宏观页雷达区 | `macro_fetcher.py` + `macro_ai_service.py` + `macro_notifier.py` | P1 |
| 日历能力 | 财经日历页与事件数据 | 部分完成 | Web `calendar` 页 | `/api/calendar/*` | P1 |
| 通知系统 | 通知中心与推送偏好 | 已完成 | Web 设置页、移动端通知页 | `/api/notifications/*`、`/api/notification-settings/*` | P1 |
| 通知系统 | 飞书价格/指标警报推送 | 已完成 | 后台调度 | `notification_service.py` + scheduler | P1 |
| AI 模型管理 | 内置模型 + BYOK | 已完成 | 设置页 AI 模型管理 | `system_ai_registry` + 用户模型接口 | P1 |
| 模拟交易 | 创建与列表查看 | 已完成 | Web/移动端模拟交易页 | `/api/paper-trading/*` | P1 |
| 模拟交易 | 后台持仓监控/自动止盈止损 | 已完成 | 后台调度 | `scheduler_jobs.py:run_refresh_simulated_trades_job` | P1 |
| 量化因子 | 因子列表/研究/信号 | 骨架已入库 | Web `quant` 页 | `/api/quant-factors/*`、`/api/signals/*` | P2 |
| 回测引擎 | 回测参数/结果 | 骨架已入库 | Web `quant` 页相关区域 | `/api/backtest/*`、回测服务 | P2 |
| 选股器 | 条件筛选与结果列表 | 部分完成 | Web `screener` 页 | `/api/screener/*` | P2 |
| 自选分组 | 股票列表/分组管理 | 骨架已入库 | 待接入独立页面 | `/api/stock-lists/*` | P2 |
| 组合风险 | 风险指标与优化建议 | 骨架已入库 | 待接入组合扩展页 | `/api/portfolio-risk/*` | P2 |
| Truth Tracker | MAE/MFE 数据沉淀 | 已完成 | `analysis_reports` 模型字段 | `max_drawdown` / `max_favorable_excursion` | P2 |
| Truth Tracker | 胜率看板/复盘面板 | 部分完成 | 前端可视化待加强 | 待持续补齐 | P2 |
| 商业化 | FREE/PRO 分层能力 | 部分完成 | 用户模型与功能开关 | `membership_tier`、订阅模型 | P2 |
| 商业化 | 支付与订阅闭环 | 骨架已入库 | 待接入完整前端流程 | `/api/subscription/*` | P3 |
| Academy | 新手引导/内容化能力 | 骨架已入库 | Web `onboarding` 页 | `/api/academy/*`、引导相关模型 | P3 |
| 监控运维 | 服务监控与诊断接口 | 已完成 | 运维侧使用 | `/api/monitoring/*` + Prometheus + `/health` + `/readiness` | P3 |
| 运维能力 | 自动部署（GH Actions + ACR） | 已完成 | CI/CD | `.github/workflows/deploy.yml` + `docker-compose.prod.yml` | P2 |

---

## 3. 后端架构基线（2026-05）

### 3.1 核心分层

| 层级 | 目录 | 职责 |
|------|------|------|
| 路由层 | `api/v1/endpoints/*` | 入参校验、调用服务、返回响应 |
| 服务层 | `services/*` | 核心业务编排、外部服务调用 |
| 用例层 | `application/{analysis,portfolio}/*` | Use Case 编排（AI 分析、组合操作） |
| 模型层 | `models/*` | SQLAlchemy ORM 定义 |
| 仓库层 | `infrastructure/db/repositories/*` | 数据访问与查询封装 |
| 核心层 | `core/*` | 配置、数据库连接、lifespan、中间件 |

### 3.2 近期架构变更

| 变更 | 日期 | 影响 |
|------|------|------|
| `main.py` 拆分为 lifespan + middleware | 2026-04 | 启动逻辑和中间件独立文件 |
| `ai_service.py` 拆分为 model_resolver + provider_router | 2026-04 | AI 调用链路解耦，支持多供应商路由 |
| 全量替换 `datetime.utcnow()` → `utc_now_naive()` | 2026-04 | 消除废弃 API，统一时间处理 |
| 新增 `start.sh` 代理可达性检测 + Tsinghua 镜像回退 | 2026-05 | 大陆环境启动更稳定 |
| 昂贵端点接入速率限制（slowapi） | 2026-04 | 防止 AI 调用被滥用 |
| StockCapsule 模型与刷新任务 | 2026-04 | 新闻/基本面 24h 自动刷新 |

---

## 4. 研发交付清单（提交前必查）

| 检查项 | 要求 | 是否阻塞提测 |
|--------|------|--------------|
| 需求范围确认 | 确认变更属于当前已落地或已入库能力域 | 是 |
| 后端契约变更 | 更新 schema、OpenAPI，并自测兼容性 | 是 |
| 前端类型同步 | 重新生成或同步类型定义，消除漂移 | 是 |
| 异常路径处理 | 至少覆盖鉴权失败、超时、三方失败 | 是 |
| 文档同步 | README/SOP/状态矩阵至少更新一处相关项 | 是 |
| 数据迁移 | 涉及表结构时必须提供 Alembic migration | 是 |
| 运行验证 | 本地 `dev` 模式可启动并跑通主链路 | 是 |

---

## 5. 测试验收清单（最小回归集）

### 5.1 P0 必测

| 场景 | 验证点 | 预期结果 |
|------|--------|----------|
| 登录与鉴权 | token 生成、刷新、过期重登 | 可登录，失效后可恢复或正确跳转 |
| 持仓管理 | 新增、编辑、删除、列表刷新 | 数据与页面展示一致 |
| 个股 AI 诊断 | 发起诊断、超时容错、结果渲染 | 成功返回结构化结果，失败可提示 |
| 行情展示 | 首页/详情页价格与关键指标展示 | 数据存在且无明显错位 |

### 5.2 P1 必测

| 场景 | 验证点 | 预期结果 |
|------|--------|----------|
| 组合分析 | 报告生成与展示 | 可生成并显示完整内容 |
| 宏观雷达 | 宏观主题、快讯、刷新 | 页面可见最新内容，异常时可降级 |
| 财经日历 | 数据读取、日期切换、空态处理 | 可见事件列表，异常状态可识别 |
| 通知系统 | 去重策略、推送偏好 | 避免重复轰炸，开关生效 |
| AI 模型管理 | 切换默认、连通性测试、BYOK 保存 | 配置可用且不泄露敏感信息 |
| 模拟交易基础 | 创建、列表读取、后台监控 | 基础链路可用，止盈止损自动触发 |

### 5.3 P2 关注项

| 场景 | 验证点 | 当前判断 |
|------|--------|----------|
| 选股器 | 条件组合、返回结果、空结果提示 | 需结合真实数据联调 |
| 量化/回测 | 参数校验、耗时任务反馈、结果展示 | 后端与前端仍在成型 |
| 组合风险 | 指标口径、异常数据处理 | 仍需补足入口与验证 |
| Truth Tracker 可视化 | 胜率、MAE/MFE 面板完整性 | 仍需产品化增强 |
| 会员能力分层 | FREE/PRO 权限边界 | 仍需与商业化联动验证 |

---

## 6. 运行与环境核查清单

| 项目 | 核查内容 | 备注 |
|------|----------|------|
| 后端环境变量 | `DATABASE_URL`、`SECRET_KEY`、AI Provider Key | 缺失会阻塞主链路 |
| 数据库 | Neon/PostgreSQL 可连接，迁移已到 `head` | 禁止手改线上表结构 |
| Redis | 可连通，用于通知去重、缓存、调度器分布式锁 | 非主存储但影响体验 |
| 调度器 | 启动后是否正常拉起并写日志 | 影响宏观、摘要、StockCapsule 刷新 |
| 前端环境变量 | `NEXT_PUBLIC_API_URL` 正确 | 影响所有 API 调用 |
| 代理环境 | `start.sh` 自动检测不可达代理并清除 | 大陆开发环境无需手动处理 |

---

## 7. 版本维护规则

1. 每次功能状态发生变化时，必须同步更新本矩阵。
2. 新增页面、接口、模型或迁移进入仓库后，至少应补记为"部分完成"或"骨架已入库"。
3. 本文档与 PRD、README、SOP 冲突时，以代码实际行为为准，并在同一迭代内统一修正。
