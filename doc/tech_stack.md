# tech_stack.md

# Technology Stack & Development Guidelines

## 1. Project Overview

**Name:** AI Smart Investment Advisor
**Type:** Web Application (SaaS Architecture)
**Goal:** Provide real-time stock tracking and AI-driven investment analysis using MCP (Model Context Protocol) concepts.

## 2. Frontend Stack

- **Framework:** Next.js 14+ (App Router directory structure `/app`).
- **Language:** TypeScript (Strict mode enabled).
- **Styling:**
    - Tailwind CSS (Utility-first).
    - `clsx` and `tailwind-merge` for class management.
- **UI Component Library:**
    - **Shadcn/UI** (Based on Radix UI).
    - Icons: Lucide React.
- **Data Visualization (Charts):**
    - **Recharts** (Preferred for financial time-series data).
- **State Management & Data Fetching:**
    - React Context (for global user state).
    - SWR or TanStack Query (React Query) (for caching API responses).
    - Axios (HTTP Client).
- **Form Handling:**
    - React Hook Form.
    - Zod (Schema validation).

## 3. Backend Stack

- **Framework:** FastAPI (Python).
- **Language:** Python 3.10+.
- **Server:** Uvicorn (ASGI).
- **Database ORM:**
    - **SQLAlchemy (AsyncIO version)** is MANDATORY.
    - **Alembic** for database migrations.
- **Data Validation:** Pydantic V2 (Strict schemas for all Request/Response).
- **Authentication:**
    - OAuth2 with Password (Bearer JWT).
    - `passlib[bcrypt]` for password hashing.
- **Financial Data Engines:**
    - `yfinance` (Yahoo Finance API wrapper).
    - `akshare` (for Chinese A-shares, optional future integration).
    - `pandas` & `pandas_ta` (for Technical Analysis indicators like RSI, MACD).
- **AI Integration:**
    - `google-generativeai` (Official Gemini SDK).
    - `openai` (Python client, compatible with DeepSeek API).

##