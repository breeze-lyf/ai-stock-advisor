# AI Stock Advisor 项目准则 (Project Rules)

## 1. 核心技术栈架构 (Architecture Context)

- **Frontend**: Next.js 14+ (App Router), Tailwind CSS, Lucide React.
- **Backend**: Python (FastAPI), pandas-ta.
- **AI Model**: 优先使用硅基流动 API 调用 DeepSeek-R1 或 Qwen3。

## 2. UI 渲染与样式准则 (UI/UX Standards)

- **风格**: 专业金融风（Slate/Zinc 灰阶），语义化配色（🔴 跌 🟢 涨 🔵 止盈 ⚪ 中性）。
- **组件化**: 可重用 React 组件（如 Trade Axis, Sentiment Bias）。

## 3. 量化逻辑与 RAG 准则 (Quant & RAG Logic)

- **数据来源**: 严禁 AI 视觉识别价格。基于后端 JSON（RSI, MACD 等）。
- **国内服务器适配 (No-Proxy Policy)**:
  - 服务器环境无代理，禁止依赖需要挂梯子的外部 API（如原生 Yahoo Finance）。
  - 必须实现国内镜像源（如 AkShare 的东财/新浪接口）作为备份或首选。
- **盈亏比**: 默认低于 1:1.5 时标记为“低性价比”。
- **实时性**: 优先集成 MCP 或实时金融 API，滞后不超过 1 分钟。

## 4. 代码质量与流程 (Code Quality)

- **TypeScript**: 强制严格类型，禁止 any。
- **错误处理**: 完善的 try-catch 和用户侧提示。
- **注释**: 复杂公式必须有详细注释。
- **测试**: 开发者手动测试，不要自动调用 Chrome。
