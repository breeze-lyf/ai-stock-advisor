# 05. 大陆环境生产部署指南 (Mainland Deployment)

**背景：** 本应用服务器地处中国上海（阿里云），受严格的网络防火墙（GFW）与跨境网速限制影响，标准的“克隆-安装”流程往往会因为 `yfinance` 等包不可达、或者 npm 卡死而失败。  
本指南记录了项目成功部署的防坑 SOP。

---

## 1. 环境总览与包管理源加速

- **OS**: Ubuntu 24.04 LTS
- **Node**: NPM 强制切换淘宝源 `npm config set registry https://registry.npmmirror.com`
- **Python**: pip 强制使用清华源或阿里源 `pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`

## 2. 前置设施：Neon PostgreSQL 绑定

我们在生产环境抛弃了 SQLite 换取并发性能。
1. 在 `.env.production` (纯后端) 中注入 `DATABASE_URL`，指向您的 Neon DB 的 `pooled` 连接池地址。
2. **连接池陷阱**：在使用 Asyncpg 时，如果使用 PgBouncer / Neon Pooling，请务必保证 SSL 是强制的，否则握手会失败 `?ssl=require`，连接语句如： `postgresql+asyncpg://user:pass@ep-...pooler.../neondb?ssl=require`

## 3. Python 后端（FastAPI）守护进程配置

由于服务器资源限制，不推荐使用 Docker 加重内存负担。直接使用纯净的 `venv` 环境并由 `PM2` 进程管理守护。

```bash
# 1. 建立虚拟环境
cd /root/ai-stock-advisor/backend
python3 -m venv venv
source venv/bin/activate

# 2. 安装防卡死依赖
pip install --upgrade pip
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 3. 压秒级启动 Uvicorn (必须用 PM2 守护)
# 为什么要用 PM2 管理 python？因为 PM2 支持开机自启、奔溃重载，且占用比系统级 systemd 脚本更容易观察。
pm2 start "venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers" --name "stock-backend"
```

## 4. Next.js 生产环境构建策略

在 1 核 2G 或类似低配云服务器上执行 `next build` 有 90% 概率会 OOM 宕机（被 Kernel OOM Killer 强杀）。

**两种部署方案的选择：**
*   **(首选) 本地预构建同步法**：在本地开发机执行完整的 `npm run build`，随后使用 `rsync` 仅推送 `.next` 目录和必要的运行文件上云。
    ```bash
    # 示例上传脚本 (排除源码和其他开发环境垃圾)
    rsync -avz --exclude 'node_modules' .next public package.json root@47.x.x.x:/root/ai-stock-advisor/frontend/
    ```
*   **(次选) SWAP 扩容保全法**：紧急情况下强行在云端 build，必须先创建一个 2GB 大小的 Swap 交换文件。

启动前端：
```bash
cd /root/ai-stock-advisor/frontend
npm i --production --registry=https://registry.npmmirror.com
pm2 start "npm run start" --name "stock-frontend"
```

## 5. 跨域与防火墙检查清单

遇到 502 / CORS 问题的排查顺序：
1. **云安全组白名单**：是否已在阿里云控制台开放 TCP `3000` (前端) 和 `8000` (后端)。
2. **CORS 放行**：在 `backend/app/main.py` 的中间件配置中，`allow_origins` 中必须包含云服务器的公网 IP 或具体调用的正式域名，本地测试通过的泛匹配在线上可能抓不到。
3. **环境变量绑定**：前端的 `.env.production` 中，`NEXT_PUBLIC_API_URL` 绝对不可填 `localhost:8000`，必须填入正式的外网地址（例如 `http://47.100.109.73:8000`）。
