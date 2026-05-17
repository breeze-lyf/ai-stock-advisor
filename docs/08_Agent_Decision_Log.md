# 08. Agent 决策日志

**定位：** 本文档记录每次 AI 协作后沉淀下来的长期设计决定、现实假设和有意接受的权衡。它不是流水账，也不是任务清单，而是帮助后续 Codex/Claude Code 理解“为什么当时这样设计”的项目记忆。

---

## 核心产品判断

- 核心问题：帮助个人投资者把分散的持仓、行情、宏观、新闻和 AI 分析整理成可行动、可追踪、可复盘的判断辅助。
- 当前阶段不做自动实盘交易系统；产品重点是分析、提醒、模拟交易、风险提示和研究辅助。
- AI 输出必须被视为辅助意见，不是投资承诺；涉及真实市场信息时，优先保留数据来源、更新时间和失败降级状态。

## 6 个月现实规模假设

- 用户规模按个人/小团队早期产品估计，而不是大规模券商级平台。
- 数据量按数百到数千用户、每人几十到数百持仓/关注标的设计。
- 架构优先支持稳定迭代和可观测性，不提前引入复杂微服务、事件总线或多区域部署。
- 性能优化优先放在缓存、批处理、后台调度、超时控制和昂贵 AI 调用限流上。

## 架构原则

- 单体优先，边界清晰：保持 FastAPI 后端为主应用，通过模块分层而不是服务拆分来管理复杂度。
- 契约优先：后端 schema、OpenAPI、前端生成类型和 UI 展示必须同步演进。
- 故障可降级：行情、宏观、搜索、AI Provider 任一外部依赖失败时，尽量返回部分结果和清晰错误，而不是让主页面崩溃。
- 用户密钥优先安全：BYOK 凭据必须走加密存储、脱敏展示和受控解析，不把明文 key 传到日志或前端状态里长期保存。
- AI 可追踪：AI 生成内容应尽量保留输入来源、模型/Provider 路由、缓存和失败原因，方便复盘。

## 应避免的依赖和复杂度

- 避免为早期规模引入 Kubernetes、复杂微服务拆分、独立消息队列集群或多数据库读写分离。
- 避免把券商交易、支付订阅、量化回测、AI Agent、通知系统一次性做成大平台式抽象。
- 避免在前端组件里散落 API URL、鉴权处理、超时策略和响应结构转换。
- 避免绕过现有 AI Provider 路由直接调用某个临时模型或供应商 SDK。

## 当前有意接受的权衡

- 接受单体后端在一段时间内承担较多职责，用清晰目录和测试边界换取开发速度。
- 接受部分高级能力先以“骨架已入库”存在，例如量化因子、回测、订阅、Academy，但交付判断必须以状态矩阵为准。
- 接受 provider/network 测试依赖外部环境，因此默认不纳入稳定 CI，只在相关任务中显式运行。
- 接受部署链路以 Docker + GitHub Actions + Aliyun ACR/server pull mode 为主，暂不追求多云部署。

## 会话结束更新规则

每次 AI 协作结束前，如果本次做出了长期有效的产品、架构、依赖、安全或测试策略决定，在本节下方追加一条简短日志。

日志格式：

```md
### YYYY-MM-DD - Short title

- Decision:
- Assumption:
- Tradeoff:
- Follow-up:
```

只记录会影响后续开发判断的内容。普通代码改动、一次性 bug、临时排查过程不要写进来。

## Session Logs

### 2026-05-17 - Establish Codex project memory

- Decision: Use root `AGENTS.md` as the Codex equivalent of `CLAUDE.md`, and keep it focused on durable working agreements.
- Assumption: This project is still early enough that architecture should optimize for single-repo iteration, safety, and explicit contracts over large-platform complexity.
- Tradeoff: Keep per-session detail out of `AGENTS.md` to avoid startup context bloat; store durable decisions in this log instead.
- Follow-up: When major product scope or architecture assumptions change, update this file and reference the change from `AGENTS.md` if it affects daily agent behavior.

### 2026-05-17 - Keep README as project homepage

- Decision: Root `README.md` should act as the project homepage: product positioning, startup commands, architecture entry points, doc navigation, deployment overview, and AI collaboration memory.
- Assumption: Detailed product scope, implementation status, database design, AI architecture, and historical decisions belong in `docs/**`, not in the root README.
- Tradeoff: The README intentionally duplicates a small amount of high-level context from docs so newcomers can orient quickly, while deferring authoritative details to the linked baseline documents.
- Follow-up: When new major modules become active, update the README overview and `docs/05_Current_Feature_Status_Matrix.md` together.

### 2026-05-17 - Add architecture overview diagrams

- Decision: Add `docs/09_Architecture_Overview.md` as the canonical architecture map for system diagrams, key Module/Seam descriptions, and major Mermaid flows.
- Assumption: Architecture understanding should start from the current modular monolith and its deepest interfaces: frontend feature API modules, backend use cases, `MarketDataService`, `AIService`, `ModelResolver`, `ProviderRouter`, `NotificationServiceV2`, and the scheduler.
- Tradeoff: The overview intentionally stays diagram-first and does not duplicate all implementation detail from SOP, status matrix, or service files.
- Follow-up: Update the architecture overview when AI Provider routing, market data provider strategy, notification policy, or scheduler task registration changes materially.

### 2026-05-17 - Organize docs by reading path

- Decision: Optimize `docs/README.md` around reading paths and document responsibility instead of deleting or immediately splitting existing documents.
- Assumption: The current document set is small enough to keep flat, but `01_Product_Requirements_Document.md` is too large to serve as a daily entry point.
- Tradeoff: Keep all current baseline documents in place to avoid breaking links, while making `docs/README.md` the source of truth for which document to read first.
- Follow-up: If docs continue to grow, split the long PRD into a product subdirectory and move repeated Agent architecture material from `06`/`07` into `09`.

### 2026-05-17 - Move long PRD into product docs

- Decision: Move the full PRD to `docs/product/01_Product_Requirements_Document.md` and add `docs/product/README.md` as the short product entry point.
- Assumption: The full PRD is valuable as a product reference, but too large and speculative for daily engineering navigation.
- Tradeoff: This adds one subdirectory but keeps the long document intact and avoids deleting product context.
- Follow-up: If product docs continue growing, split the full PRD into smaller product files by audience or lifecycle stage.
