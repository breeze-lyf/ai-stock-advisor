/**
 * Cloudflare Worker - Yahoo Finance 代理
 * 
 * 部署步骤:
 * 1. 登录 https://developers.cloudflare.com/workers/
 * 2. 创建新 Worker，粘贴此代码
 * 3. 设置环境变量 PROXY_KEY (随机字符串，用于鉴权)
 * 4. 记录 Worker URL (如：https://yahoo-proxy.your-account.workers.dev)
 * 
 * 使用方式:
 * GET https://<worker-url>/?url=https://query2.finance.yahoo.com/v8/finance/chart/NVDA&x-proxy-key=<your-key>
 */

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    
    // CORS 预检请求
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, OPTIONS',
          'Access-Control-Allow-Headers': 'X-Proxy-Key, Content-Type',
        },
      });
    }

    // 验证请求来源 (简单鉴权)
    const authHeader = request.headers.get('X-Proxy-Key');
    if (authHeader !== env.PROXY_KEY) {
      return new Response('Unauthorized', { 
        status: 401,
        headers: { 'Content-Type': 'text/plain' }
      });
    }

    // 获取目标 URL
    const targetUrl = url.searchParams.get('url');
    if (!targetUrl || !targetUrl.includes('finance.yahoo.com')) {
      return new Response('Invalid URL', { 
        status: 400,
        headers: { 'Content-Type': 'text/plain' }
      });
    }

    try {
      // 转发请求到 Yahoo
      const response = await fetch(targetUrl, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
          'Accept': 'application/json, text/plain, */*',
          'Accept-Language': 'en-US,en;q=0.9',
        },
        cf: {
          cacheEverything: true,
          cacheTtl: 60, // 60 秒缓存
        },
      });

      // 返回响应
      return new Response(response.body, {
        status: response.status,
        headers: {
          'Content-Type': response.headers.get('Content-Type') || 'application/json',
          'Access-Control-Allow-Origin': '*',
          'Cache-Control': 'public, max-age=60',
        },
      });
    } catch (error) {
      return new Response(JSON.stringify({ error: error.message }), {
        status: 500,
        headers: { 
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        },
      });
    }
  }
};
