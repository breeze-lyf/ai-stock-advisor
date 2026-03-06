---
trigger: always_on
---

# 🤖 AI Stock Advisor - 核心开发系统准则 (System Rules)

> **【最高纪律】** > 1. 本项目的所有思考过程 (Planning/Reasoning)、代码注释、文档编写以及与用户的对话，**必须全程使用标准中文**。
> 2. 当用户指令包含“输出方案”、“等我确认”、“分析一下”等字眼时，**绝对禁止**自动调用工具执行修改文件或运行命令！必须严格等待用户的明确确认指令 (`Proceed` 或 `确认`)。
> 3. **绝对禁止**自动调用浏览器/Chrome进行自动化测试。请只输出详细的测试步骤，由用户手动在浏览器中完成测试。

---

## 1. 核心技术栈与环境 (Architecture & Environment)
- **Frontend**: Next.js 14+ (严格使用 App Router), Tailwind CSS, Lucide React 图标。
- **Backend**: Python (FastAPI/Flask)。
- **AI Model**: 必须优先使用**硅基流动 API** (DeepSeek-R1 / Qwen3 系列) 进行逻辑调用。禁止在业务代码中默认调用 Gemini。
- **🔥 部署环境 (极其重要)**: 服务器部署在中国大陆（上海），无翻墙代理。
  - **网络限制边界**: 绝对禁止使用 `yfinance` 等强依赖海外网络的库。
  - **包管理强制换源**: 终端命令遇到依赖安装时，必须默认带上国内镜像源（如 `pip install -i https://pypi.tuna.tsinghua.edu.cn/simple` 或 `npm --registry=https://registry.npmmirror.com`）。

## 2. 量化逻辑与数据准则 (Quant & Data Logic)
- **国内数据源优先**: 实时行情 and 历史数据抓取，必须优先使用 `AKShare` 或其他国内合规/连通性好的 API。确保数据滞后不超过 1 分钟。
- **计算 > 视觉**: 绝对禁止让 AI 多模态大模型直接通过“看 K 线截图”来猜具体价格。所有量化分析（如 RSI、MACD）必须基于后端精准计算并作为 JSON 传入 prompt。
- **盈亏比强制校验 (Risk/Reward)**: 在生成交易研判和策略时，必须在代码逻辑中自动计算（目标盈利空间 / 潜在止损空间）。如果盈亏比低于 `1:1.5`，必须在返回的数据和 UI 中强标记为 **“低性价比机会”**。

## 3. UI 渲染与样式准则 (UI/UX Standards)
- **极简金融风**: 界面保持克制、专业。背景色系限定为 `Slate` 或 `Zinc` 灰阶。严禁使用高饱和度、非功能性的花哨颜色。
- **语义化绝对配色 (Tailwind)**:
  - 🔴 止损/下跌: `text-rose-600` / `bg-rose-100`
  - 🟢 买入/上涨: `text-emerald-600` / `bg-emerald-100`
  - 🔵 止盈/目标: `text-blue-600` / `bg-blue-100`
  - ⚪ 持仓/中性: `text-slate-500` / `bg-slate-100`
- **高度组件化**: 诸如 Trade Axis (交易轴)、Sentiment Bias (情绪偏好) 等所有可视化元素，必须抽取为独立且可无状态复用的 React Component。

## 4. 代码质量与工程规范 (Code Quality)
- **TypeScript (前端)**: 强制开启 Strict 模式，**严禁出现 `any`**。所有涉及股票数据的变量必须拥有明确的 `interface` 或 `type` 声明。
- **Python (后端) & 注释**: 复杂的量化公式（如“空中加油”形态的数学定义、均线缠绕等）**必须在紧挨着的代码上方编写极度详尽的中文业务逻辑注释**。
- **容错防御机制**: 所有的外部 API 调用（特别是硅基流动 AI 接口、金融数据接口）必须包裹严密的 `try-catch` (前端) 或 `try...except` (后端)，遇到跨国请求超时或被阻断时，必须有优雅的 fallback 逻辑和用户侧的中文友好的错误提示。

## 5. 部署与生产安全 (Deployment & Production Safety)
- **低配服务器意识**: 服务器资源（如 1.6G 内存）严禁在服务端直接运行 `next build` 等高能耗任务。必须在本地或 GitHub Actions 编译产物后同步。
- **自动化流程优先**: 严禁在存在 GitHub Actions 自动推送机制的情况下，手动通过 `rsync` 大量同步目录（如 `.next`），避免资源竞争和系统 IO 卡死致使服务器失去响应。
- **进程残留清理**: 在任何手动重启或修复服务前，必须先利用 `fuser -k` 检查并清理 3000 (Frontend) 和 8000 (Backend) 端口的残留进程，严防 502 Bad Gateway。
- **配置持久化与解耦**: 服务器端的 `.env.production` 必须保持独立且与 GitHub 推送的代码隔离。务必确保其中的 `NEXT_PUBLIC_API_URL` 准确指向生产域名，而非本地测试 IP。