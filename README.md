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
