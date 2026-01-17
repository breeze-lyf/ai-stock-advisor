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

- `/backend`: FastAPI application, database models, and market data logic.
- `/frontend`: Next.js dashboard and UI components.
- `/doc`: Project documentation and PRD.
