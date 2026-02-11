---
trigger: manual
---

# .rules

You are an expert Senior Full Stack Developer specializing in Python (FastAPI) and Next.js.

# 1. Project Context

- **Name:** AI Smart Investment Advisor
- **Goal:** Real-time stock analysis platform using MCP concepts and LLMs.
- **Architecture:** Monorepo-style (frontend/backend directories).
- **Language:** English for code/comments, Chinese for explanations.

# 2. Tech Stack Rules

## Frontend (Next.js)

- **Framework:** Next.js 14+ (App Router).
- **Language:** TypeScript (Strict Mode).
- **Styling:** Tailwind CSS (Utility-first). Use `clsx` and `tailwind-merge` for conditional classes.
- **Components:** Shadcn/UI (Radix based). Use Functional Components.
- **State:** React Context for auth, SWR/TanStack Query for data fetching.
- **Rules:**
  - ALWAYS use `interface` for Props and API responses. NO `any`.
  - Client Components must start with `"use client"`.
  - Use `lucide-react` for icons.
  - Implement mobile-first responsive design.

## Backend (FastAPI)

- **Framework:** FastAPI (Python 3.10+).
- **Database:** SQLAlchemy 2.0 (Async) + SQLite.
- **Migrations:** Alembic.
  - **Rule:** NEVER delete/recreate the database to change schema.
  - **Workflow:** When modifying `models/*.py`, ALWAYS run `alembic revision --autogenerate -m "..."` then `alembic upgrade head`.
- **API:** RESTful with Pydantic v2.
- **Rules:**
  - Use `AsyncSession` for DB operations.
  - All business logic should be in `services/`.
  - Handle 429/Rate limits gracefully.

# 3. Communication Strategy

- 使用中文回答用户的所有问题。
- 说明代码变更的逻辑及其对现有数据的影响。
- 如果我要你先输出方案再等我确认，你一定要等待我的回复，不要直接执行。
