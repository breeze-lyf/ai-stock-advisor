# CLAUDE.md

这个文件是项目的持久化契约——"为什么这么设计"的共识。
操作规范（怎么做）在 `AGENTS.md`，实现细节在 `docs/`。

---

## 1. 核心问题

这个产品帮助**个人投资者**做出更有依据的投资判断：看懂自己持仓的风险、理解宏观变化对组合的影响、在信息不对称时获得 AI 辅助的第二意见。

它不是量化交易系统，不是自动下单机器人，不是专业机构工具。目标用户是有一定投资经验但缺乏专业分析能力的散户。

---

## 2. 当前阶段假设（2026-05，有效期约 6 个月）

| 维度 | 当前假设 |
|------|----------|
| 用户规模 | 10-100 人小圈子早期用户 |
| 核心目标 | 打磨已有功能的质量与稳定性，保持架构清晰，不扩展功能边界 |
| 商业化 | 不在这个阶段推进订阅/支付闭环 |
| 基础设施 | 继续依赖外部 AI provider 和数据源，不自建 |
| 部署 | 单机 Docker Compose，不需要多实例或 K8s |

**这些假设改变时，此文件需要重新校准。**

---

## 3. 架构原则

### 3.1 统一模式优先于局部最优

同类问题必须复用现有的实现方式，不新造模式。

- 新增 AI 调用走 `ai_service.py` → `model_resolver.py` → `provider_router.py`，不绕过这条链路
- 新增数据拉取走 `market_providers/` 下的 provider 模式，不在 endpoint 里直接调外部 API
- 新增通知走 `notification_service.py`，不在 scheduler job 里直接发推送

如果现有模式无法满足需求，先讨论再改模式，不要悄悄绕开。

### 3.2 AI 输出结构必须向后兼容

AI 输出字段的任何变动都必须同步完成完整链路：

```
backend schema → openapi.json → npm run generate-types → 前端渲染组件
```

禁止只改一头。部分完成的链路比不改更危险。

### 3.3 失败必须可见

静默失败比显式报错更危险。

- 行情拉取失败：必须记录日志，返回带错误标记的响应，不返回空数据假装成功
- AI 调用失败：必须区分 auth 错误、模型不存在、超时、可重试的服务错误
- 通知推送失败：必须写 notification_logs，不能静默丢弃
- 调度任务异常：必须有可观测的失败状态，不能让 scheduler 静默跳过

---

## 4. 有意接受的权衡

### 接受

- **外部依赖**：AI provider（DashScope/OpenAI/DeepSeek）、行情数据（AkShare/YFinance）、宏观数据（Tavily/财联社）都依赖第三方，不自建。
- **单机部署**：Docker Compose 单机足够支撑当前规模。
- **骨架功能延后**：量化/回测/选股/自选分组等 P2/P3 骨架功能，在当前阶段不主动扩展，除非用户明确要求。

### 不接受

- **技术债**：不为了"先跑起来"接受职责混乱、目录混杂、命名不一致。发现就改，越早越便宜。
- **架构漂移**：同类功能出现两种实现方式时，必须统一，不能并存。每次新加功能前先确认现有模式。
- **职责混杂**：一个目录/文件不应同时承担基础设施适配、业务编排、领域逻辑三种性质的代码。
- **前后端类型漂移**：backend schema 和前端类型不同步是不可接受的状态，发现立刻修复。

---

## 5. 给 Claude Code 的工作约定

- 遇到"应该在哪里实现"的判断，先看 `AGENTS.md` Repository Map，找到最近的现有模式
- 遇到"这个功能要不要做"的判断，对照 `docs/05_Current_Feature_Status_Matrix.md` 的状态，P2/P3 骨架不主动触碰
- 每次会话结束后，把做了什么决定、引入了什么假设，追加一条到下方的会话日志

---

## 6. 会话决策日志

<!-- 格式：YYYY-MM-DD: [决策内容] — [原因] -->
<!-- 满 30 条后将旧条目归档到 docs/archive/ -->

2026-05-17: 创建 CLAUDE.md，采用精简契约方案（方案 A）— 文件越短越能保证 AI 每次完整读取；AGENTS.md 保持不动，两者分工为"为什么"vs"怎么做"
2026-05-17: 改变立场——不再接受技术债 — 用户判断"早做便宜"，把"接受技术债"从权衡里移除并加入"不接受职责混杂"。这意味着后续重构按需进行，不再以"先跑起来"为借口推迟。
2026-05-17: 删除 notification_service v1 façade — 业务代码 0 引用，仅一个非 pytest 集成脚本依赖；v2 自带飞书发送能力，无能力损失。修复了 v1/v2 并存的架构漂移。
2026-05-17: 修正"AI 调用有侧路"的误判 — 之前凭印象判断 macro_ai_service / enhanced_ai_analysis 绕过主链，实际两者都走 AIService。教训：批评架构前必须读代码，不读就下结论是不可接受的。
2026-05-17: 完成 services/ 重构（7 个 commit）— 原 35 个文件混杂的 services/ 被拆为三个明确目录：integrations/（AI provider 栈 + email + market_providers + indicators + fetchers）、domain/（market/macro/portfolio/quant/analysis/notifications 六个 bounded context）、scheduler/（cron 编排）。ai_service.py 保留在 services/ 根作为顶层编排。同时清理 3 个死代码文件（paper_trading_scheduler/ai_provider_client/macro_persistence），保留 factor_engine 待量化骨架激活时使用。每个 commit 后 pytest 31 passed + app.main 可启动。
