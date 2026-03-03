# 🤖 AI Smart Investment Advisor (AI 智能股票策略顾问)

> **工业级 AI 量化决策辅助系统**。基于 Next.js 14 (App Router) 与 FastAPI 构建，深度整合 DeepSeek 研判模型与国内避墙数据源。

---

## 🌟 核心特性 (Key Features)

### 1. 🎯 精准量化可视化 (Trade Axis)
- **决策价位锚定坐标系**：摒弃常规等分刻度，采用核心价位驱动（止损/建仓/加码/目标）的非线性坐标轴。
- **视觉冲突规避**：自动处理重合价位（如“止损”与“加码”重合）的渲染逻辑，确保决策点 100% 视觉对齐。

### 2. 🌐 全球宏观热点雷达 (Macro Radar)
- **5 小时自动巡检**：定时全网扫描影响市场的宏观事件、地缘政治风险及货币政策转向。
- **高可用推送体系**：
  - **飞书 BOT 集成**：整点推送 AI 提炼的 3-5 个核心宏观题材及其对持仓标的的穿透分析。
  - **断网/额度降级**：当海外新闻 API (Tavily) 受限时，系统自动切换至 **财联社本地降级数据源** 确保研判永不断流。
  - **智能去重**：针对摘要类消息开启 1 分钟级动态去重，兼顾个股预警的严肃性与快讯的灵活性。

### 3. 🛡️ 大陆环境深度优化 (Mainland China Optimized)
- **零代理数据抓取**：深度利用 `AkShare` 避开 `yfinance` 等海外网络依赖。
- **混合行情引擎**：美股采用腾讯/新浪行情镜像，A股采用东财/网易镜像，确保行情滞后 < 1 分钟。
- **全栈时区管理**：支持从数据库底层到前端 UI 的统一时区偏移配置（UTC+8 默认）。

### 4. 🧠 机构级 AI 研判逻辑
- **DeepSeek-R1 驱动**：使用 SiliconFlow 高速接口进行深度逻辑推演。
- **盈亏比强制校验**：系统自动计算目标盈利空间与潜在止损空间的比例，低于 `1:1.5` 的机会将强力标记。

---

## 🚀 快速启动 (Quick Start)

项目提供了一键启动快捷脚本，可自动检测环境并启动前后端：

```bash
chmod +x start.sh
./start.sh
```

---

## 🛠 系统架构与技术栈

### 前端 (Frontend)
- **核心框架**: Next.js 14 (App Router)
- **样式方案**: Tailwind CSS (遵循 `Slate/Zinc` 极简金融风)
- **交互组件**: Radix UI + Lucide Icons
- **可视化**: 物理像素校准的自定义 React 交易轴组件

### 后端 (Backend)
- **核心框架**: FastAPI (Python 3.10+)
- **任务调度**: 常驻后台协程 (轮询精度 60s)
- **数据库**: SQLite / PostgreSQL (SQLAlchemy Async)
- **AI 引擎**: SiliconFlow API (DeepSeek V3 / R1)

---

## 📂 项目结构布局

### 后端核心目录
- `backend/app/services/macro_service.py`: 宏观雷达与财联社快讯降级逻辑核心。
- `backend/app/services/notification_service.py`: 飞书 Webhook 签名安全校验与去重算法。
- `backend/app/services/scheduler.py`: 负责整点摘要生成的调度中心。
- `backend/app/core/database.py`: 异步 Session 管理逻辑。

### 前端核心目录
- `frontend/components/features/StockDetail.tsx`: 包含复杂的交易轴 (Trade Axis) 渲染算法。
- `frontend/lib/utils.ts`: 全局 `formatDateTime` 时区转换方案。
- `frontend/app/settings/page.tsx`: 全局用户信息与时区偏好配置。

---

## ⚠️ 部署注意事项 (Mainland Deployment)

1. **环境变量**: 确保 `.env` 中正确配置 `FEISHU_WEBHOOK_URL` 与 `SILICONFLOW_API_KEY`。
2. **包管理换源**: 
   - Python: `pip install -i https://pypi.tuna.tsinghua.edu.cn/simple`
   - Node: `npm --registry=https://registry.npmmirror.com`
3. **数据库初始化**: 运行 `backend/scripts/init_db.py` 补充初始标的。

---

## 🔗 数据源致谢
- 金融数据: AKShare
- 实时快讯: 财联社 (Cailianshe)
- 搜索支持: Tavily API

---
© 2026 AI Smart Investment Advisor - 让决策更理智。
