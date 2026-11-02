# Agent P2：个人投资智能体（简报 / 复盘 / 试用 / 画像 / 功能开关）

分支：`feat/agent-p2`。迁移：`e8b2c3d4f5a6`（down_revision `d7a1b2c3e4f5`，**只新增 3 张表，无改动/删除**）。

## 产品结构

| 路由 | 说明 |
|---|---|
| `/` | 未登录：公开落地页（3 个价值点、截图、CTA→`/try`/注册）；已登录：智能体首页（对话 + 今日简报 + 持仓/自选异动 + 战绩概览） |
| `/briefs` | 每日简报列表、手动生成 / 生成并推送 |
| `/dashboard?tab=portfolio` | 持仓与自选（原仪表盘，次级入口；`tab=analysis` 为个股诊断） |
| `/review` | 复盘战绩：命中率、方向收益均值、建议明细 |
| `/settings` | 投资画像、推送渠道、通用、通知、安全；**高级设置**（折叠）：AI 模型（BYOK/多供应商）、数据源 |
| `/try` | 免登录试用 |
| `/agent` | 智能体页（与登录后的 `/` 相同） |

## 后端 API（`/api/v1/agent`）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/briefs?limit=` | 简报列表 + `scheduled`/`hour` |
| POST | `/briefs/generate?push=` | 生成今日简报（同日覆盖），可选推送；3 次/小时 |
| GET/POST | `/notifiers` | 推送渠道（最多 5 个；`kind`=dingtalk/webhook/telegram，URL 与 secret 用 `ENCRYPTION_KEY` 加密） |
| DELETE | `/notifiers/{id}` | 删除 |
| POST | `/notifiers/{id}/test` | 发送测试消息；10 次/小时 |
| GET | `/advice?status=` | 建议记录 + 统计 |
| GET | `/public-config` | 公开：试用开关/额度、billing 开关、定时简报开关 |
| POST | `/trial/chat` | 公开：试用对话；每 IP 每日 `AGENT_TRIAL_DAILY_LIMIT` 次（429） |

投资画像沿用已有 `GET/POST /api/v1/user-profile/profile`（`UserInvestmentProfile`），作为智能体长期记忆注入系统提示词（同时注入持仓与自选列表）。

## 建议记录与复盘

- 来源：`run_stock_diagnosis` 工具结果（diagnosis）、智能体回答末尾的标签行 `【建议】代码|BUY/SELL/HOLD|天数|理由`（agent，标签行在展示前被剥离）、简报中的标签行（brief）。
- 记录时取当时价格；同一用户同一标的同方向 24h 内去重。
- 调度器每天 17:00（北京时间）评估到期记录：BUY 收益>0 命中；SELL 收益<0 命中；HOLD 跌幅不超过 5% 命中。无基准价或逾期 7 天仍取不到价格 → `error`。
- 与已有 `AISignalHistory`/signals 模块有概念重叠：P2 独立建表以免影响既有逻辑，后续可合并。

## 每日简报

- 默认关闭：`AGENT_BRIEF_ENABLED=true` 后，调度器在每天 `AGENT_BRIEF_HOUR`:00–:14（北京时间）为有持仓/自选的用户生成，Redis 锁 `agent:brief:{date}` 保证多实例只跑一次（无 Redis 时退化为本地执行）。
- 简报智能体只用只读数据工具（不跑重型诊断），生成后推送到用户启用的渠道。

## 免登录试用

- 只允许 `get_quote / get_kline_and_technicals / get_fundamentals / search_news / macro_snapshot`，`user=None`，不落库。
- 只用系统 LLM 中转（消耗系统额度），`AGENT_TRIAL_MAX_STEPS` 限步。
- IP 取 `X-Real-IP` → `X-Forwarded-For` 首项 → socket；**生产 nginx 需设置 `proxy_set_header X-Real-IP $remote_addr;`**，否则所有用户共享一个额度或可伪造。

## 功能开关与隐藏项

前端 `frontend/shared/config/features.ts`（`NEXT_PUBLIC_FEATURE_*`，构建时生效），后端 `FEATURE_BILLING_ENABLED`。隐藏 ≠ 删除，页面仍可按 URL 访问。

| 隐藏项 | 开关 | 原因 |
|---|---|---|
| FREE/PRO 会员徽章（订阅/计费 UI） | `NEXT_PUBLIC_FEATURE_BILLING` | 无支付闭环，展示会误导 |
| 量化因子 `/quant` | `NEXT_PUBLIC_FEATURE_QUANT` | 骨架阶段、专业向、与个人智能体主线无关 |
| 模拟交易 tab | `NEXT_PUBLIC_FEATURE_PAPER_TRADING` | 独立玩法，基础版，非主流程 |
| 财经日历 `/calendar` | `NEXT_PUBLIC_FEATURE_CALENDAR` | 部分完成；智能体新闻/宏观工具已覆盖 |
| 热点雷达 tab | `NEXT_PUBLIC_FEATURE_RADAR` | 智能体内置 `macro_snapshot`，简报会汇总 |
| 选股器 `/screener` | `NEXT_PUBLIC_FEATURE_SCREENER` | 部分完成，非主流程 |
| 用户菜单 `/alerts`（死链） | — | 修正为 `/dashboard?tab=alerts`（推送记录） |
| BYOK / 多供应商 / 数据源 | 设置 → 高级设置（折叠） | 新用户无需配置，系统模型即可用 |

## 新增环境变量

见 `.env.example`：`AGENT_BRIEF_ENABLED`(false)、`AGENT_BRIEF_HOUR`(8)、`AGENT_BRIEF_MAX_USERS`(200)、`AGENT_ADVICE_REVIEW_ENABLED`(true)、`AGENT_TRIAL_ENABLED`(true)、`AGENT_TRIAL_DAILY_LIMIT`(5)、`AGENT_TRIAL_MAX_STEPS`(4)、`FEATURE_BILLING_ENABLED`(false)，以及前端 `NEXT_PUBLIC_FEATURE_*`。推送渠道依赖 `ENCRYPTION_KEY`。

## 截图

改版前：`docs/images/before/`；改版后：`docs/images/after/`。

## 视觉改版与涨跌配色（Phase 3）

- 设计令牌集中在 `frontend/app/globals.css`：单一靛蓝强调色 `brand`，`canvas/surface/elevated/line/ink` 分层，`card / num / eyebrow / skeleton` 工具类，深浅色均通过令牌切换。
- **涨跌配色可配置**：价格涨跌一律使用语义色 `text-up / text-down / bg-up-soft / bg-down-soft`（K 线用 `priceHex()`），不再硬编码红绿。
  - 默认 **绿涨红跌**（`green_up`），可在 设置 → 外观与显示 切换为 **红涨绿跌**（`red_up`），带实时预览。
  - 存储：`users.price_color_mode`（迁移 `f1c2d3e4a5b6`），经 `PUT /api/v1/user/settings` 保存；同时缓存在 `localStorage.price_color_mode`，`<head>` 内联脚本在首屏前设置 `html[data-updown]`，未登录页面同样生效。
- `/try` 入口默认隐藏：`NEXT_PUBLIC_FEATURE_TRIAL` 默认 `false`（页面与后端开关保留）。登录/注册页下方旧营销区块（合作方、定价、占位数据）以 `SHOW_AUTH_MARKETING=false` 隐藏。
- 截图：`docs/images/after/`（桌面 1440/1280，浅色/深色，两种涨跌配色）与 `docs/images/after/mobile/`（390）。
