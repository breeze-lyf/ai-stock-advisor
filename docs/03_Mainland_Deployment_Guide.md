# 03. 大陆环境部署指南 (Mainland Deployment Guide)

**定位：** 本文档对齐当前 README 与开发 SOP 的统一口径，描述大陆网络环境下可执行、可维护的部署流程。  
**更新时间：** 2026年4月2日。

---

## 1. 统一部署结论

当前推荐方案：

1. GitHub Actions 构建镜像并推送 GHCR。
2. 服务器只执行拉镜像与 docker compose 启动。
3. 数据库优先使用 Neon Postgres（或接入自有 PostgreSQL），应用侧统一走 `DATABASE_URL`。

不再推荐把“后端 venv + PM2 + 前端手动构建”作为主流程，仅可作为应急临时方案。

---

## 2. 环境与网络前置

### 2.1 服务器建议

- OS: Ubuntu 22.04+/24.04
- Docker + Docker Compose Plugin
- 可访问 GHCR
- 已配置时区与基础安全策略（SSH、fail2ban、最小开放端口）

### 2.2 大陆网络加速建议

- npm 镜像：`https://registry.npmmirror.com`
- pip 镜像：`https://pypi.tuna.tsinghua.edu.cn/simple`

说明：生产推荐走镜像分发后，服务器通常不再需要频繁执行 npm/pip 安装。

---

## 3. 数据库策略

支持两种主流模式：

### 3.1 本地 PostgreSQL

适用场景：私有化部署、内网合规、已有数据库体系。

- 在环境变量中设置 `DATABASE_URL` 指向可达 PostgreSQL 实例。
- 若后端容器连接宿主机数据库，可使用 `host.docker.internal`（按系统能力确认）。
- 应用部署前先完成迁移：`alembic upgrade head`。

### 3.2 Neon Postgres（可选云端）

适用场景：轻运维、弹性扩缩容、快速上线。

- 在环境变量中设置 `DATABASE_URL` 指向 Neon 连接串。
- 连接串需满足 SSL 要求（如 `sslmode=require`）。
- 保持与迁移脚本一致，不允许手改表结构。

---

## 4. 推荐部署流程（GHCR + docker-compose.prod）

### 4.1 GitHub 侧准备

需要配置以下 Secrets：

- `SERVER_IP`
- `SERVER_USER`
- `SSH_PRIVATE_KEY`
- `GHCR_USERNAME`
- `GHCR_TOKEN`（需要 read:packages）
- `NEXT_PUBLIC_API_URL`

关键文件：

- `.github/workflows/deploy.yml`
- `docker-compose.prod.yml`
- `scripts/deploy_compose_prod.sh`

### 4.2 服务器侧准备

1. 创建应用目录并放置生产编排文件。
2. 准备 `backend/.env`（仅服务器使用，不与本地复用）。
3. 登录 GHCR：

```bash
echo "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USERNAME" --password-stdin
```

### 4.3 发布命令（服务器）

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

### 4.4 发布后校验

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=200 backend
docker compose -f docker-compose.prod.yml logs --tail=200 frontend
```

---

## 5. 环境变量最小清单

后端关键变量（示例）：

- `DATABASE_URL`
- `SECRET_KEY`
- `DASHSCOPE_API_KEY`
- `DASHSCOPE_BASE_URL`（可选）
- `IS_SERVER_ENV`（默认 false）
- 其他 AI Provider Key（按实际启用）
- 飞书 webhook/通知相关变量（按需）

可选代理变量（仅在需要通过 Cloudflare Worker 中转 Yahoo 时启用）：

- `CLOUDFLARE_WORKER_URL`
- `CLOUDFLARE_WORKER_KEY`

前端关键变量：

- `NEXT_PUBLIC_API_URL`（必须是可访问后端地址，不能写 localhost）

---

## 6. 大陆环境专项建议

1. 默认启用代理可达性检查，代理不可达时自动清理进程代理变量。
2. 配置 `AKSHARE_BYPASS_PROXY=true`，确保 AkShare 相关国内域名直连。
3. 对跨境不稳定源保持降级策略，宏观/快讯链路优先保证可用性。
4. 生产上尽量避免“在线构建前端大包”，优先镜像化分发。

### 6.1 数据源智能路由

系统会根据 `IS_SERVER_ENV` 自动选择美股数据源：

- `IS_SERVER_ENV=false`（默认，本地环境）：美股优先 YFinance，A 股/港股用 AkShare。
- `IS_SERVER_ENV=true`（服务器环境）：美股与 A 股/港股都走 AkShare，提升无代理环境可用性。

### 6.2 Cloudflare Worker 代理（可选）

当服务器环境需要补齐 Yahoo 美股数据时，可启用 Worker 代理：

1. 部署 `cloudflare-worker/yahoo-proxy.js` 到 Cloudflare Workers。
2. 配置 `CLOUDFLARE_WORKER_URL` 与 `CLOUDFLARE_WORKER_KEY`。
3. 验证后端日志是否出现 Worker 代理成功命中。

---

## 7. 监控与运维基线

1. 日志统一查看容器日志，必要时接入 Loki/Grafana。
2. 每次发布后检查：健康状态、关键接口、调度任务是否拉起。
3. 数据库变更执行顺序：迁移 -> 应用发布。
4. 定期检查镜像版本与回滚点，保留最近稳定镜像标签。

---

## 8. 常见故障排查顺序

### 8.1 502 / 网关错误

1. `backend` 容器是否健康启动。
2. `NEXT_PUBLIC_API_URL` 是否指向正确地址。
3. 反向代理（如 Nginx）上游配置是否与端口一致。

### 8.2 CORS 错误

1. 后端 CORS 白名单是否包含实际前端域名。
2. 前端是否错误调用了 localhost 地址。
3. 反向代理是否覆盖了 Origin/Host 头。

### 8.3 AI 调用失败

1. API Key 是否有效。
2. 模型 ID 是否在对应供应商可用。
3. 网络/超时策略是否触发回退链路。

### 8.4 数据库连接失败

1. `DATABASE_URL` 是否正确且可达。
2. Neon SSL 参数是否完整。
3. 发布前后迁移是否一致。

---

## 9. 文档一致性约束

本文件与以下文档保持同一口径：

- `README.md`
- `docs/01_Product_Requirements_Document.md`
- `docs/02_Developer_SOP_and_Guide.md`
- `docs/05_Current_Feature_Status_Matrix.md`

若四者出现冲突，以“代码实际行为”优先，并在同一迭代内同步修正。
