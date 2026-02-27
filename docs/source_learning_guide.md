# AI Stock Advisor 源码学习导读

欢迎开始学习本项目！这份手册将引导你逐步掌握这个“人工智能量化分析系统”的内部工作原理。代码中已为你补齐了保姆级的中文注释。

---

## 🚀 核心架构概览

把本项目想象成一个“人”：
- **模型 (Models)** 是骨架：定义了我们能存储什么信息。
- **服务 (Services)** 是大脑：负责思考、抓取数据、计算指标。
- **API (Endpoints)** 是手脚：负责与外部（前端）沟通。
- **前端 (Frontend)** 是皮肤和五官：负责展示给用户看。

---

## 📅 阶段性学习路线图

### 第一阶段：理解数据脉络 (Data Foundation)
> **目标**：搞清楚数据库里存了什么，以及这些字段在现实金融世界中代表什么意义。

- **核心代码**:
    1.  **[backend/app/models/stock.py](file:///Users/breeze/Dev/ai-stock-advisor/backend/app/models/stock.py)**: 重点看价格、RSI、MACD 等缓存字段。
    2.  **[backend/app/models/analysis.py](file:///Users/breeze/Dev/ai-stock-advisor/backend/app/models/analysis.py)**: 理解 AI 诊断结果的结构化存储。
    3.  **[backend/app/core/database.py](file:///Users/breeze/Dev/ai-stock-advisor/backend/app/core/database.py)**: 学习异步连接池与 SQLite 性能优化。

| 维度 | 详情 |
| :--- | :--- |
| **学习方法** | 对照 `doc/er_diagram.md` 的 Mermaid 图阅读代码字段定义。 |
| **预估耗时** | 0.5 - 1 小时 |
| **难度等级** | ⭐ (入门) |
| **补充知识** | SQLAlchemy 基础、数据库范式、异步编程 `asyncio`。 |

---

### 第二阶段：理解量化逻辑 (Quant & Services)
> **目标**：掌握如何通过代码计算金融指标，以及如何调教大模型生成投资决策。

- **核心代码**:
    1.  **[backend/app/services/indicators.py](file:///Users/breeze/Dev/ai-stock-advisor/backend/app/services/indicators.py)** ⭐: 学习 MACD、KDJ 的纯 Python 实现。
    2.  **[backend/app/services/market_data.py](file:///Users/breeze/Dev/ai-stock-advisor/backend/app/services/market_data.py)**: 探究如何优雅地处理多源行情抓取。
    3.  **[backend/app/services/ai_service.py](file:///Users/breeze/Dev/ai-stock-advisor/backend/app/services/ai_service.py)** ⭐: 重点看 Prompt (提示词) 模板的设计技巧。

| 维度 | 详情 |
| :--- | :--- |
| **学习方法** | 手动修改一个指标参数（如将 RSI 周期从 14 改为 7），观察计算值的变化。 |
| **预估耗时** | 2 - 3 小时 |
| **难度等级** | ⭐⭐⭐ (核心/挑战) |
| **补充知识** | Pandas 基础、技术面分析 (TA) 常识、RAG (检索增强生成) 概念。 |

---

### 第三阶段：理解前后端通讯 (Bridge)
> **目标**：理解 Web 系统的 API 是如何“打包”和“传递”数据的。

- **核心代码**:
    1.  **[backend/app/api/v1/endpoints/analysis.py](file:///Users/breeze/Dev/ai-stock-advisor/backend/app/api/v1/endpoints/analysis.py)**: 看 FastAPI 的路由定义。
    2.  **[frontend/lib/api.ts](file:///Users/breeze/Dev/ai-stock-advisor/frontend/lib/api.ts)**: 看前端如何封装 Fetch 请求。

| 维度 | 详情 |
| :--- | :--- |
| **学习方法** | 使用浏览器调试工具 (F12) 观察 Network 选项卡，看每一次接口调用的输入输出。 |
| **预估耗时** | 0.5 - 1 小时 |
| **难度等级** | ⭐⭐ (进阶) |
| **补充知识** | RESTful API 规范、TypeScript Interface、HTTP 状态码。 |

---

### 第四阶段：理解前端交互 (UI/UX)
> **目标**：学习如何将复杂的金融数据通过 React 可视化组件呈现给用户。

- **核心代码**:
    1.  **[frontend/components/features/TradeAxis.tsx](file:///Users/breeze/Dev/ai-stock-advisor/frontend/components/features/TradeAxis.tsx)**: 学习如何自定义渲染一个交易中轴线。
    2.  **[frontend/app/page.tsx](file:///Users/breeze/Dev/ai-stock-advisor/frontend/app/page.tsx)**: 理解 React 的状态提升与组件通信。

| 维度 | 详情 |
| :--- | :--- |
| **学习方法** | 尝试修改界面上的颜色（如 Tailwind 类名中的 `bg-rose-600` 改为 `bg-blue-600`）。 |
| **预估耗时** | 1 - 2 小时 |
| **难度等级** | ⭐⭐ (进阶) |
| **补充知识** | React Hooks、Tailwind CSS、Lucide 图标库。 |

---

## 💡 终极学习技巧
- **全案搜索**：遇到不认识的变量（如 `ticker`），在 VS Code 中用 `Ctrl+Shift+F` 搜索它在全项目中出现的地方。
- **对比阅读**：一边看后端的 `Service` 逻辑，一边看它对应的前端 `Component` 渲染，打通任督二脉。
- **勇于“破坏”**：尝试注释掉某行核心逻辑，看看程序在哪里崩溃，这能帮你迅速建立逻辑感。
