---
trigger: always_on
---

1. 核心技术栈架构 (Architecture Context)
   Frontend: 使用 Next.js 14+ (App Router), Tailwind CSS, 以及 Lucide React 图标。

Backend: 使用 Python (FastAPI/Flask) 处理量化逻辑，集成 pandas-ta 进行指标计算。

AI Model: 优先使用硅基流动 API 调用的 DeepSeek-R1 或 Qwen3 系列模型。

2. UI 渲染与样式准则 (UI/UX Standards)
   专业金融风: 界面必须保持克制、理性，使用 Slate 或 Zinc 灰阶作为背景，严禁使用高饱和度、非功能性的装饰性颜色。

语义化配色: \* 🔴 止损/下跌: text-rose-600 / bg-rose-100。

🟢 买入/上涨: text-emerald-600 / bg-emerald-100。

🔵 止盈/目标: text-blue-600 / bg-blue-100。

⚪ 持仓/中性: text-slate-500 / bg-slate-100。

组件化: 所有的可视化组件（如 Trade Axis, Sentiment Bias）必须作为独立、可重用的 React 组件编写。

3. 量化逻辑与 RAG 准则 (Quant & RAG Logic)
   计算优先: 禁止让 AI 视觉模型通过图片识别价格。所有分析必须基于后端传入的精确 JSON 数值（如 RSI、MACD 详细值）。

盈亏比校验: 在生成交易研判逻辑时，必须自动计算盈利空间与亏损空间的比例（Reward/Risk），且默认盈亏比低于 1:1.5 时需标记为“低性价比机会”。

实时性: 编写数据抓取逻辑时，优先考虑集成 MCP 协议或实时金融 API（如 Yahoo Finance），确保信息滞后不超过 1 分钟。

4. 代码质量要求 (Code Quality)
   TypeScript: 强制使用严格类型，禁止使用 any。对于股票数据结构，定义清晰的 interface 或 type。

错误处理: 在处理 API 调用（如硅基流动接口）时，必须包含完善的 try-catch 逻辑和用户侧的错误提示。

注释规范: 复杂的量化公式（如空中加油形态的数学定义）必须在代码上方编写详细的逻辑注释。

5.其他要求
回答以及思考过程全程需要使用中文
当我让你输出方案等我确认再执行时，你本次回答就不要执行开发任务，一定要等到我明确的确认指令
你不要自动调用chrome进行测试，你只需要告诉我怎么测试，由我来手动测试
在新的需要调用ai的功能点开发过程中，优先使用硅基流动的api来调用ai，而不是gemini
让你创建的文档需要是中文的
写代码一定要加注释