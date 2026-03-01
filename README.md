# AI Smart Investment Advisor

An AI-powered stock analysis platform helping investors make data-driven decisions.

## 🚀 Quick Start

The easiest way to run the entire stack (Backend + Frontend) is using the helper script:

```bash
chmod +x start.sh
./start.sh
```

## 🛠 Manual Setup

### 1. Backend (FastAPI)

```bash
cd backend
# Create virtual env (optional but recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run Server
uvicorn app.main:app --reload
```
Server: http://localhost:8000  
Docs: http://localhost:8000/docs

### 2. Frontend (Next.js)

```bash
cd frontend
# Install dependencies
npm install

# Run Dev Server
npm run dev
```
Frontend: http://localhost:3000

## 📂 Project Structure

### Backend (FastAPI)

- `backend/app/api/v1/`: Versioned endpoints (Analysis, Portfolio, Auth, User).
- `backend/app/services/market_providers/`: Modular data providers (yfinance, Alpha Vantage).
- `backend/app/services/indicators.py`: Centralized technical indicator calculations.
- `backend/scripts/`: Deployment and database utility scripts.
- `backend/tests/`: Automated test suite.

### Frontend (Next.js)

- `frontend/app/`: App router pages.
- `frontend/components/features/`: Extracted business logic components (PortfolioList, StockDetail, etc).
- `frontend/components/ui/`: Reusable Shadcn base components.
- `frontend/types/`: Centralized TypeScript interfaces.
- `frontend/lib/api.ts`: API client with Axios interceptors.

## ⚠️ Important: Mainland Server Deployment
For deployment on servers in mainland China without a proxy:
- **5 小时自动全球雷达扫描**：每 5 小时自动巡检全球宏观风险，并向飞书推送汇总简报。
- **消息面深度优化 (New)**：
    - **雷达鲜度优先**：引入 Upsert 机制，相同题材热点在重复探测时仅更新时间戳与逻辑，杜绝冗余，确保“最新热点即时置顶”。
    - **财联社内容清洗 (New)**：
        - **AI 摘要提炼**：针对深度头条，系统自动调用 DeepSeek 将长篇网页内容提炼为 150 字以内的研判精华，彻底杜绝网页杂质。
        - **正则噪声过滤**：自动识别并剔除快讯中的页脚、免责声明、版权信息等视觉噪音。
        - **全量数据进化**：已对数据库进行净化处理，确保现有快讯流整洁清爽。
    - **增强型 RAG 分析**：AI 引擎现已能识别头条权重，确保个股建议具备更强的机构级研判深度。
- **Market Data**: The system automatically uses domestic mirrors (East Money/Sina) via AkShare for both US and A-shares.
- **Proxy Conflict**: The system is designed to bypass proxies for domestic data sources automatically to prevent 403 errors.
- **AI News**: US news might be restricted without a proxy; domestic news remains accessible.
