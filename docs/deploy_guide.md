# AI Stock Advisor 阿里云上海服务器部署指南

由于服务器位于中国上海，部署过程中需要特别注意跨境访问的网络环境（GFW）。本指南将详细记录从零开始的部署步骤。

## 📍 服务器信息

- **IP**: 47.100.109.73 (上海)
- **操作系统**: Ubuntu 24.04 LTS
- **用户**: root

---

## 🛠 第一步：系统环境初始化 (正在进行...)

### 1.1 确认系统软件源

阿里云官方 Ubuntu 镜像已经默认配置了内网镜像源 (`mirrors.cloud.aliyuncs.com`)，无需手动修改，更新速度极快。

```bash
apt update && apt upgrade -y
```

### 1.2 安装基础工具

```bash
apt install -y git curl wget build-essential python3-venv python3-pip
```

### 1.3 安装 Node.js (v18+)

本项目 Next.js 14 要求 Node.js >= 18.17。

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs
# 验证版本
node -v  # 应输出 v20.x
npm -v
```

---

## 📦 第二步：项目同步

我们使用 `rsync` 将本地代码推送到服务器。

```bash
# 在本地机器执行 (请替换为实际的密钥路径)
rsync -avz --exclude 'node_modules' --exclude '.next' --exclude 'venv' --exclude '.git' ./ root@47.100.109.73:/root/ai-stock-advisor/
```

---

## 🐍 第三步：后端服务配置 (Python)

### 3.1 创建虚拟环境

```bash
cd /root/ai-stock-advisor/backend
python3 -m venv venv
source venv/bin/activate
```

### 3.2 安装依赖

由于在上海，必须使用国内 PyPI 镜像（阿里云或豆瓣），否则安装 `pandas`, `numpy` 等大包会极慢。

```bash
pip install --upgrade pip
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

### 3.3 环境配置文件 (.env)

在 `backend` 目录下创建 `.env`。

```bash
# 示例配置
DATABASE_URL=sqlite+aiosqlite:///../ai_advisor.db
SECRET_KEY=yoursecretkeyhere
ALPHAVANTAGE_API_KEY=yourkey
# 境外 API 代理 (如果需要)
# HTTP_PROXY=http://127.0.0.1:xxxx
# 注意：在上海服务器上，美股和 A 股行情均会自动通过 AkShare 的国内镜像获取，无需代理。
# 只有在本地开发且已安装 Clash 时，才建议启用代理以获得极速 Yahoo Finance 体验。
```

---

## 🌐 第四步：前端服务配置 (Next.js)

### 4.1 安装依赖

由于在上海，使用淘宝镜像 (NPMmirror) 极大加速。

```bash
cd /root/ai-stock-advisor/frontend
npm install --registry=https://registry.npmmirror.com
```

### 4.2 构建项目

```bash
npm run build
```

---

## 🚀 第五步：进程管理 (PM2)

我们使用 PM2 来守护进程，确保服务器重启后程序能自动运行。

### 5.1 启动后端

```bash
cd /root/ai-stock-advisor/backend
# 启动 uvicorn
pm2 start "venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000" --name "stock-backend"
```

### 5.2 启动前端

```bash
cd /root/ai-stock-advisor/frontend
# 启动 next start
pm2 start "npm run start" --name "stock-frontend"
```

### 5.3 保存并设置开机自启

```bash
pm2 save
pm2 startup
```

---

## 🛡 第六步：最后检查与排查

1.  **防火墙**：确保阿里云控制台开放了 **3000** 和 **8000** 端口。
2.  **日志查看**：执行 `pm2 logs` 监控实时输出。
3.  **内网互通**：确保前端可以通过服务器公网 IP 加端口 8000 访问到后端 API。

### 🐞 常见问题排查 (Troubleshooting)

- **Next.js 导出错误**: 在根页面直接调用 `useSearchParams()` 且未包裹 `Suspense` 会导致打包失败。已通过 `DashboardContent` 包装解决。
- **数据库表名冲突**: `stock.py` 和 `portfolio.py` 曾竞争 `portfolios` 表名，已清理冗余定义。
- **Pydantic 顺序问题**: Schema 定义需保证被引用者在前。

## 📅 后续建议
1. **安全组配置**: 前往阿里云后台，开放 **8000** 和 **3000** 端口。
2. **域名绑定**: 配置 A 记录指向 `47.100.109.73`。
