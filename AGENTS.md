# AGENTS.md

## Project Overview

AI Smart Investment Advisor is an AI-assisted stock analysis and portfolio support system.
The active codebase centers on:

- Web frontend: Next.js 16, React 19, TypeScript, Tailwind CSS 4, Radix UI
- Backend: FastAPI, SQLAlchemy Async, Alembic, PostgreSQL/Neon, Redis
- AI layer: system model registry plus user BYOK provider configuration
- Data layer: A/H/US market data, macro radar, calendar, notifications, paper trading, quant/backtest skeletons
- Deployment: Docker images built in GitHub Actions and deployed to Aliyun ACR/server pull mode

Treat this as a production-leaning financial analysis app, not a demo. Prefer correctness, traceability, and safe failure modes over clever shortcuts.

## Language

- Use Chinese when interacting with the user unless the user explicitly asks for another language.
- Keep technical terms such as API, schema, migration, provider, and hook in English when that is clearer.

## 安全约束（必读）

- 禁止使用任何脚本批量删除文件或目录。
- 只能使用 `Remove-Item` 一个一个文件地删除。
- 如果必须批量删除，必须停止操作让用户手动确认。

## Architecture Contract

- Treat `docs/08_Agent_Decision_Log.md` as the durable record of why the product and architecture are shaped this way.
- Optimize for the next 6 months of realistic early-product scale: a clear modular monolith, explicit contracts, safe AI/provider behavior, and observable failures.
- Do not introduce platform-level complexity such as Kubernetes, broad microservice splits, new queue clusters, or multi-cloud deployment unless the user has agreed that scale now requires it.
- At the end of a meaningful session, append only durable decisions, assumptions, and tradeoffs to `docs/08_Agent_Decision_Log.md`; do not turn `AGENTS.md` into a running diary.

## First Files To Read

Before non-trivial work, read the relevant local docs in this order:

1. `README.md` for current startup and repo navigation.
2. `docs/02_Developer_SOP_and_Guide.md` for architecture and delivery rules.
3. `docs/05_Current_Feature_Status_Matrix.md` for implemented vs partial vs skeleton features.
4. `docs/04_Database_Design.md` when touching models, migrations, or persistence.
5. `docs/06_AI_Analysis_Implementation_Guide.md` and `docs/07_Agent_Architecture_Design.md` when touching AI analysis, provider routing, or tool-augmented agent behavior.
6. `docs/08_Agent_Decision_Log.md` when making product, architecture, dependency, safety, or testing tradeoffs.

If docs conflict with code, trust the code, then update the affected doc in the same change when practical.

## Common Commands

Start the full local stack:

```bash
./scripts/start.sh dev
```

Start with Docker:

```bash
./scripts/start.sh docker
docker compose up --build -d
```

Backend dev server:

```bash
cd backend
../.venv/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend dev server:

```bash
cd frontend
npm run dev -- -p 3000
```

Frontend checks:

```bash
cd frontend
npm run lint
npm run build
npm run generate-types
```

Backend tests:

```bash
pytest backend/tests/unit -q
pytest backend/tests/integration -q
RUN_PROVIDER_NETWORK_TESTS=1 pytest backend/tests/provider -q
```

Database migrations:

```bash
cd backend
alembic revision --autogenerate -m "your_migration_name"
alembic upgrade head
```

## Repository Map

- `frontend/app/**`: Next.js App Router pages and route-level composition.
- `frontend/components/features/**`: business UI components.
- `frontend/components/ui/**`: reusable primitive UI components.
- `frontend/features/**/api.ts`: domain API clients, hooks, request mapping.
- `frontend/shared/api/client`: shared API client; keep auth and error handling centralized.
- `frontend/types/schema.d.ts`: generated OpenAPI types.
- `backend/app/api/v1/endpoints/**`: FastAPI routers; keep them thin.
- `backend/app/application/**`: use-case orchestration for analysis and portfolio workflows.
- `backend/app/services/**`: business services, provider integrations, scheduler jobs, AI routing.
- `backend/app/models/**`: SQLAlchemy ORM models.
- `backend/app/schemas/**`: Pydantic request/response contracts.
- `backend/app/infrastructure/**`: persistence and repository details.
- `backend/migrations/**`: Alembic migrations.
- `backend/tests/unit/**`: fast logic tests.
- `backend/tests/integration/**`: API/DB integration tests.
- `backend/tests/provider/**`: network/provider tests, opt-in only.
- `docs/**`: product, SOP, database, status matrix, deployment, and AI architecture docs.
- `scripts/**`: startup and deployment scripts.
- `.local/**`, `backend/.local/**`, `frontend/node_modules/**`, `__pycache__/**`: generated/local state; do not edit unless explicitly asked.

## Backend Rules

- Keep routers thin: validate inputs, call services/use cases, return schemas.
- Put business flow in `application/**` or `services/**`, not in endpoint files.
- Use SQLAlchemy Async patterns consistently; avoid introducing sync DB calls into async request paths.
- Structure changes must go through Alembic. Do not hand-edit production tables or add SQLite fallbacks.
- Use `DATABASE_URL` and existing config helpers; do not hardcode database URLs.
- Sanitize market/provider data before persistence. Guard against `NaN`, missing values, malformed tickers, and third-party timeout errors.
- Scheduler/background jobs must be cancellable, logged, and safe to retry. Respect Redis locks and deduplication behavior.
- External errors returned to users must not expose stack traces, secrets, raw API keys, or internal connection strings.

## AI And Provider Rules

- Do not hardcode temporary model names in business logic. Use the existing model registry and resolver flow.
- Preserve the AI chain split:
  - `backend/app/services/ai_service.py` for orchestration and prompt/caching flow.
  - `backend/app/services/model_resolver.py` for model config, user credentials, and API key resolution.
  - `backend/app/services/provider_router.py` for provider dispatch, failover, connection tests, and caching.
- BYOK keys must flow through user/provider credential models and encryption/decryption helpers. Never log plaintext keys.
- Provider failures should distinguish auth/model-not-found/timeout/retryable service failures where possible.
- AI outputs that feed UI should remain structured and backward compatible. If fields change, update schemas, OpenAPI, generated frontend types, and rendering components together.
- For tool-augmented agent features, require source labels, verification status, and graceful partial results instead of unsupported confident claims.

## Frontend Rules

- Keep `frontend/app/**` focused on routing, page loading, and composition. Move reusable business logic into `features/**` or `components/features/**`.
- Put API calls in `frontend/features/**/api.ts` or the shared client layer, not scattered inside components.
- Prefer generated OpenAPI types from `frontend/types/schema.d.ts`; avoid `any` unless the boundary is genuinely unknown and documented.
- Keep authentication expiration and generic request errors centralized in the shared API client.
- Settings, AI model management, notification settings, and data source configuration handle sensitive state; avoid showing raw secrets after save.
- Use existing UI primitives and lucide icons when extending controls. Keep dashboard/tool screens dense, scannable, and work-focused.
- After user-visible frontend changes, run lint/build when feasible and use a browser check for affected pages.

## Contract Change Checklist

When changing API request/response shape, complete the chain:

1. Backend model/service logic.
2. Pydantic schema in `backend/app/schemas/**`.
3. Router response/request typing.
4. `backend/openapi.json` regeneration if the project flow requires it.
5. `cd frontend && npm run generate-types`.
6. Frontend API wrapper and UI rendering updates.
7. Relevant docs/status matrix update.

Do not consider contract work done if backend and frontend types drift.

## Testing Expectations

- For narrow backend logic changes, run targeted unit tests.
- For API, auth, portfolio, AI, notification, scheduler, or DB changes, add or run relevant integration tests.
- Provider tests require network/proxy state; run them only when the task is provider-specific or explicitly requested.
- For frontend changes, run `npm run lint`; run `npm run build` for routing, data loading, type, or production behavior changes.
- For database changes, run Alembic upgrade locally against the intended dev database before declaring completion.
- If a test cannot be run because credentials, network, Redis, or database are unavailable, say exactly what was skipped and why.

## Security And Privacy

- Treat API keys, BYOK credentials, webhook URLs, JWT secrets, database URLs, SSH keys, and ACR credentials as sensitive.
- Never print secrets in logs, test output, screenshots, or final summaries.
- Be especially careful in these areas:
  - user/provider credentials and encrypted API keys
  - AI model connection testing
  - Feishu/webhook notifications
  - browser push subscriptions
  - GitHub Actions deploy secrets
  - Redis-backed locks, cache, and notification deduplication
- Do not add new production dependencies or external services without explaining why existing libraries are insufficient.

## Documentation Rules

- Keep root `README.md` focused on quick start and navigation.
- Keep `docs/02_Developer_SOP_and_Guide.md` aligned with executable development workflow.
- Keep `docs/05_Current_Feature_Status_Matrix.md` updated when feature status changes.
- Put one-off summaries and stale planning docs under `docs/archive/`, not the repository root.
- Prefer concise, current docs over long speculative roadmaps.

## Git And Worktree Rules

- Do not revert user changes unless the user explicitly asks.
- Before editing, check `git status --short` and work around unrelated dirty files.
- Keep changes scoped to the requested task.
- Do not run destructive commands such as `git reset --hard` or `git checkout --` without explicit permission.
- Final summaries should state changed files and verification performed.
