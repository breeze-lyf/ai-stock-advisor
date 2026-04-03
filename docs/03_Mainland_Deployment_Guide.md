# 03. 大陆环境部署指南 (Mainland Deployment Guide)

**定位：** 本文档对齐当前 README 与开发 SOP 的统一口径，描述大陆网络环境下可执行、可维护的部署流程。  
**更新时间：** 2026 年 4 月 3 日。

---

## 1. 统一部署结论

当前推荐方案：

1. GitHub Actions 构建镜像并推送阿里云 ACR
2. 服务器只执行拉镜像与 docker compose 启动
3. 数据库使用本地 PostgreSQL（或接入自有 PostgreSQL），应用侧统一走 `DATABASE_URL`

不再推荐把"后端 venv + PM2 + 前端手动构建"作为主流程，仅可作为应急临时方案。

---

## 2. 环境与网络前置

### 2.1 服务器建议

- OS: Ubuntu 22.04+/24.04
- Docker + Docker Compose Plugin
- 可访问阿里云 ACR
- 已配置时区与基础安全策略（SSH、fail2ban、最小开放端口）

### 2.2 大陆网络加速建议

- npm 镜像：`https://registry.npmmirror.com`
- pip 镜像：`https://pypi.tuna.tsinghua.edu.cn/simple`

说明：生产推荐走镜像分发后，服务器通常不再需要频繁执行 npm/pip 安装。

---

## 3. 数据库策略

### 3.1 本地 PostgreSQL（默认）

适用场景：私有化部署、内网合规、已有数据库体系、2G 内存服务器。

- 在环境变量中设置 `DATABASE_URL` 指向可达 PostgreSQL 实例
- 本地开发：`postgresql+asyncpg://user:pass@127.0.0.1:5432/dbname`
- 服务器 Docker：`postgresql+asyncpg://user:pass@host.docker.internal:5432/dbname`
- 应用部署前先完成迁移：`alembic upgrade head`

**本地开发环境示例**：
```bash
DATABASE_URL=postgresql+asyncpg://breeze:ServBay.dev@127.0.0.1:5432/ai_stock_advisor
```

**服务器 Docker 环境示例**：
```bash
DATABASE_URL=postgresql+asyncpg://ai_stock_app:xxx@host.docker.internal:5432/ai_stock_advisor
```

### 3.2 Neon Postgres（可选云端）

适用场景：轻运维、弹性扩缩容、快速上线、托管需求。

- 在环境变量中设置 `DATABASE_URL` 指向 Neon 连接串
- 连接串需满足 SSL 要求（如 `sslmode=require`）
- 保持与迁移脚本一致，不允许手改表结构

**Neon 连接串示例**：
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@xxx.xxx.neon.tech/dbname?sslmode=require
```

---

## 4. 推荐部署流程（阿里云 ACR + docker-compose.prod）

### 4.1 GitHub 侧准备

需要配置以下 Secrets：

- `SERVER_IP`
- `SERVER_USER`
- `SSH_PRIVATE_KEY`
- `ACR_USERNAME`（阿里云容器镜像服务用户名）
- `ACR_PASSWORD`（阿里云容器镜像服务密码）
- `NEXT_PUBLIC_API_URL`

关键文件：

- `.github/workflows/deploy.yml`
- `docker-compose.prod.yml`
- `scripts/deploy_compose_prod.sh`

### 4.2 服务器侧准备

1. 创建应用目录并放置生产编排文件
2. 准备 `backend/.env`（仅服务器使用，不与本地复用）
3. 登录阿里云 ACR：

```bash
echo "$ACR_PASSWORD" | docker login $ACR_REGISTRY -u "$ACR_USERNAME" --password-stdin
```

### 4.3 发布命令（服务器）

```bash
cd /root/ai-stock-advisor
export ACR_REGISTRY="registry.cn-hangzhou.aliyuncs.com"
export APP_IMAGE_TAG="latest"
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

### 4.4 发布后校验

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=200 backend
docker compose -f docker-compose.prod.yml logs --tail=200 frontend
curl http://localhost:8000/health
```

---

## 5. 环境变量最小清单

后端关键变量（示例）：

- `DATABASE_URL` - PostgreSQL 连接串（必填）
- `SECRET_KEY` - JWT 加密密钥（必填，32 位以上随机字符串）
- `ENCRYPTION_KEY` - API Key 加密密钥（Fernet 32 字节 base64）
- `DASHSCOPE_API_KEY` - 通义千问 API Key
- `DASHSCOPE_BASE_URL` - 通义千问 Base URL（可选）
- 其他 AI Provider Key（按实际启用）
- 飞书 webhook/通知相关变量（按需）

代理配置变量（按需）：

- `HTTP_PROXY` - 全局 HTTP 代理（如 `http://127.0.0.1:7897`）
- `HTTPS_PROXY` - 全局 HTTPS 代理
- `NO_PROXY` - 不走代理的域名列表
- `AKSHARE_BYPASS_PROXY=true` - AkShare 国内域名直连

Yahoo Finance 代理（可选）：

- `CLOUDFLARE_WORKER_URL` - Cloudflare Worker 代理 URL
- `CLOUDFLARE_WORKER_KEY` - Worker 鉴权密钥

前端关键变量：

- `NEXT_PUBLIC_API_URL` - 必须是可访问后端地址，不能写 localhost

---

## 6. 大陆环境专项建议

### 6.1 网络环境分类与配置策略

当前系统支持两种网络环境配置，但**需要手动选择**，暂无运行时自动检测切换机制：

| 环境类型 | 特征 | 配置方式 | 数据源行为 |
|----------|------|----------|-----------|
| **本地开发环境** | 有代理可用（如 Clash、Surge） | 配置 `HTTP_PROXY`/`HTTPS_PROXY` | YFinance 通过代理直连 Yahoo |
| **服务器环境** | 无代理（如阿里云无科学上网） | 配置 `CLOUDFLARE_WORKER_URL`/`KEY` | YFinance 失败后自动切换 Worker 代理 |

**当前局限性**：
- `HTTP_PROXY` 是全局配置，启动后固定生效，无法根据请求动态切换
- YFinance 的故障切换是"进程级"的：第一次失败后，后续所有美股请求都走 Worker 代理
- 无法做到"同一进程内某些请求走代理、某些不走"

**推荐配置组合**：

```bash
# 本地开发（有全局代理）
HTTP_PROXY=http://127.0.0.1:7897
HTTPS_PROXY=http://127.0.0.1:7897
AKSHARE_BYPASS_PROXY=true  # AkShare 国内域名不走代理
NO_PROXY=127.0.0.1,localhost,eastmoney.com,sina.com.cn,akshare.xyz

# 服务器（无全局代理，仅 Yahoo 走 Worker）
# 不配置 HTTP_PROXY/HTTPS_PROXY
CLOUDFLARE_WORKER_URL=https://yahoo-proxy.your-account.workers.dev
CLOUDFLARE_WORKER_KEY=your-secret-key
```

### 6.2 数据源智能路由

系统采用**统一数据源策略**，美股固定使用 YFinance，A 股/港股固定使用 AkShare：

| 股票类型 | 识别规则 | 数据源 | 故障降级 |
| :--- | :--- | :--- | :--- |
| A 股 | 6 位纯数字 (000001, 600519) | AkShare (直连) | 网易/新浪镜像 |
| 港股 | 6 位数字+.HK (00700.HK) | AkShare (直连) | 新浪镜像 |
| 美股 | 字母代码 (AAPL, NVDA) | YFinance (默认直连) | Cloudflare Worker → Yahoo |

**美股故障自动切换流程**：

```text
┌─────────────────────────────────────────────────────────────┐
│  美股数据请求                                                │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  1. YFinance 直连 (默认尝试)                                 │
│     yf.Ticker(symbol).history(...)                          │
└─────────────────────────────────────────────────────────────┘
         │
         ├─────────────────┐
         │                 │
         ▼                 ▼
   ┌───────────┐     ┌───────────┐
   │  成功     │     │  失败     │
   │ 返回数据  │     │ 设置      │
   └───────────┘     │ _use_worker_proxy=True │
                     └───────────┘
                              │
                              ▼
                     ┌───────────────────┐
                     │ 2. Cloudflare     │
                     │    Worker 代理    │
                     │    (自动切换)     │
                     └───────────────────┘
                              │
                              ▼
                     ┌───────────────────┐
                     │ 后续请求都走      │
                     │ Worker 代理       │
                     │ (进程生命周期内)  │
                     └───────────────────┘
```

**配置方式**：
- 本地环境（有代理）：YFinance 通常直连成功，无需 Worker 配置
- 服务器环境（无代理）：建议配置 `CLOUDFLARE_WORKER_URL` 和 `CLOUDFLARE_WORKER_KEY`，确保 YFinance 失败时可降级

### 6.3 Cloudflare Worker 代理（可选）

当服务器环境需要补齐 Yahoo 美股数据时，可启用 Worker 代理：

1. 部署 `cloudflare-worker/yahoo-proxy.js` 到 Cloudflare Workers（免费，每日 10 万次请求）
2. 配置 `CLOUDFLARE_WORKER_URL` 与 `CLOUDFLARE_WORKER_KEY`
3. 验证后端日志是否出现 Worker 代理成功命中

---

## 7. 监控与运维基线

1. 日志统一查看容器日志，必要时接入 Loki/Grafana
2. 每次发布后检查：健康状态、关键接口、调度任务是否拉起
3. 数据库变更执行顺序：迁移 -> 应用发布
4. 定期检查镜像版本与回滚点，保留最近稳定镜像标签
5. 关注 YFinance 切换日志：`[YFinance] Switching to Cloudflare Worker proxy`

---

## 8. 常见故障排查顺序

### 8.1 502 / 网关错误

1. `backend` 容器是否健康启动
2. `NEXT_PUBLIC_API_URL` 是否指向正确地址
3. 反向代理（如 Nginx）上游配置是否与端口一致

### 8.2 CORS 错误

1. 后端 CORS 白名单是否包含实际前端域名
2. 前端是否错误调用了 localhost 地址
3. 反向代理是否覆盖了 Origin/Host 头

### 8.3 AI 调用失败

1. API Key 是否有效
2. 模型 ID 是否在对应供应商可用
3. 网络/超时策略是否触发回退链路

### 8.4 数据库连接失败

1. `DATABASE_URL` 是否正确且可达
2. 容器连接宿主机时 `host.docker.internal` 是否可用
3. 发布前后迁移是否一致

### 8.5 美股数据缺失

1. 检查后端日志是否有 `YFinance` 相关错误
2. 确认是否已触发 Worker 代理切换
3. 验证 `CLOUDFLARE_WORKER_URL` 和 `CLOUDFLARE_WORKER_KEY` 配置
4. 测试 Worker 代理是否可访问：
   ```bash
   curl "https://your-worker.workers.dev/?url=https://query2.finance.yahoo.com/v8/finance/chart/AAPL?interval=1d&range=1mo" \
     -H "X-Proxy-Key: your-key"
   ```

---

## 9. 文档一致性约束

本文件与以下文档保持同一口径：

- `README.md`
- `docs/01_Product_Requirements_Document.md`
- `docs/02_Developer_SOP_and_Guide.md`
- `docs/05_Current_Feature_Status_Matrix.md`

若四者出现冲突，以"代码实际行为"优先，并在同一迭代内同步修正。
