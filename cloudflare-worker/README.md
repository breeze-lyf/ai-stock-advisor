# Cloudflare Worker - Yahoo Finance 代理

## 用途

解决中国大陆服务器无法访问 Yahoo Finance 的问题。通过 Cloudflare 全球边缘节点中转请求，实现：
- 上海阿里云 → Cloudflare Worker → Yahoo Finance ✅
- 无需在服务器上配置代理
- 免费额度充足（每日 10 万次请求）

---

## 部署步骤

### 1. 创建 Cloudflare Worker

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. 进入 **Workers & Pages** → **Create Application**
3. 选择 **Create Worker** → 命名为 `yahoo-proxy` → **Deploy**

### 2. 部署代码

将 `yahoo-proxy.js` 的内容粘贴到 Worker 编辑器中，点击 **Save and Deploy**。

### 3. 配置环境变量

在 Worker 页面的 **Settings** → **Variables** → **Environment Variables** 中添加：

| Variable | Value |
|---|---|
| `PROXY_KEY` | 随机生成的密钥（如 `your-secret-key-12345`） |

**保存后重新部署 Worker。**

### 4. 记录 Worker URL

部署成功后，Worker 的 URL 格式为：
```
https://yahoo-proxy.your-account.workers.dev
```

---

## 后端配置

在 `backend/.env` 中添加：

```bash
# Cloudflare Worker 代理配置
CLOUDFLARE_WORKER_URL=https://yahoo-proxy.your-account.workers.dev
CLOUDFLARE_WORKER_KEY=your-secret-key-12345
```

---

## 使用方式

### 自动使用

配置后，`YFinanceProvider` 会自动优先通过 Worker 代理访问 Yahoo Finance：

```python
from app.services.market_providers.yfinance import YFinanceProvider

provider = YFinanceProvider()
data = await provider.get_historical_data("NVDA", period="200d")
```

### 请求流程

```
1. YFinanceProvider 检查是否配置了 CLOUDFLARE_WORKER_URL
2. 如果配置了，优先通过 Worker 代理请求
3. 如果 Worker 失败，自动回退到 yfinance 直连
4. 如果直连也失败，返回 None
```

---

## API 使用示例

### 直接调用 Worker

```bash
# 请求
curl "https://yahoo-proxy.your-account.workers.dev/?url=https://query2.finance.yahoo.com/v8/finance/chart/NVDA?interval=1d&range=1mo" \
  -H "X-Proxy-Key: your-secret-key-12345"

# 响应
{
  "chart": {
    "result": [{
      "meta": { "currency": "USD", "symbol": "NVDA", ... },
      "timestamp": [1704067200, 1704153600, ...],
      "indicators": {
        "quote": [{
          "open": [495.5, 498.2, ...],
          "high": [501.3, 505.1, ...],
          "low": [493.2, 496.8, ...],
          "close": [499.1, 502.5, ...],
          "volume": [1234567, 2345678, ...]
        }]
      }
    }]
  }
}
```

---

## 成本估算

Cloudflare Workers 免费额度：
- 每日 100,000 次请求
- 每次请求最多 10ms CPU 时间
- 全球 275+ 数据中心

**对于个人项目完全够用**。如果超出，付费计划为 $5/月（1000 万次请求）。

---

## 安全说明

1. **PROXY_KEY 保密**: 不要在公开场合泄露你的密钥
2. **域名白名单**: Worker 代码已限制只能代理 `finance.yahoo.com` 的请求
3. **速率限制**: Cloudflare 自动防护 DDoS 攻击

---

## 故障排除

### Worker 返回 401 Unauthorized
- 检查 `CLOUDFLARE_WORKER_KEY` 是否与 Worker 环境变量的 `PROXY_KEY` 一致

### Worker 返回 400 Invalid URL
- 确认请求的 URL 包含 `finance.yahoo.com`
- 检查 URL 是否正确编码

### Worker 返回 500 Error
- 查看 Worker 控制台的错误日志
- 可能是 Yahoo API 暂时不可用

### 请求超时
- 检查网络连接
- 增加 httpx 超时时间（当前 15 秒）

---

## 进阶优化

### 1. 自定义域名

在 Cloudflare Dashboard 中绑定自定义域名：
```
https://yahoo.your-domain.com
```

### 2. 增加缓存时间

修改 Worker 代码中的 `Cache-Control`：
```javascript
'Cache-Control': 'public, max-age=300', // 5 分钟缓存
```

### 3. 增加请求日志

添加 Cloudflare Logpush 到你的 SIEM 系统。

---

## 替代方案

如果不想使用 Cloudflare，可以考虑：
- **自建代理服务器**: 在海外 VPS 上部署 nginx 反向代理
- **使用商业 API**: Alpha Vantage, IEX Cloud, Polygon.io
- **IBKR 数据源**: 已有集成，但需要账户

---

## 文件结构

```
cloudflare-worker/
├── yahoo-proxy.js       # Worker 源代码
└── README.md            # 本说明文档
```
