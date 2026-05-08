// Cloudflare Worker: Yahoo Finance API Proxy with Crumb Auth
// Deploy: wrangler deploy or via Cloudflare Dashboard
// Required secrets: WORKER_API_KEY

const YAHOO_CONFIG = {
  cookieUrl: 'https://fc.yahoo.com',
  crumbUrl: 'https://query2.finance.yahoo.com/v1/test/getcrumb',
  proxies: [
    { path: '/v10/finance/quoteSummary', host: 'query2.finance.yahoo.com' },
    { path: '/v7/finance/quote', host: 'query1.finance.yahoo.com' },
    { path: '/v8/finance/chart', host: 'query2.finance.yahoo.com' },
    { path: '/v1/finance/search', host: 'query2.finance.yahoo.com' },
    { path: '/v1/finance/lookup', host: 'query1.finance.yahoo.com' },
    { path: '/ws/fundamentals-timeseries', host: 'query1.finance.yahoo.com' },
    { path: '/xhr/ncp', host: 'finance.yahoo.com', method: 'POST' },
  ],
};

// Cache for cookie+crumb, 25min TTL (crumb expires ~30min)
const CACHE_TTL = 25 * 60 * 1000;
let _cache = { cookie: '', crumb: '', expires: 0 };

async function ensureAuth() {
  if (Date.now() < _cache.expires && _cache.crumb) return _cache;

  // Step 1: Get Yahoo cookie
  const cookieResp = await fetch(YAHOO_CONFIG.cookieUrl, { redirect: 'manual' });
  const setCookie = cookieResp.headers.get('set-cookie') || '';
  const cookieMatch = setCookie.match(/(^|;)\s*A3=([^;]+)/);
  if (!cookieMatch) {
    // Try alternate cookie endpoint
    const altResp = await fetch('https://consent.yahoo.com/v2/collectConsent?sessionId=3', { redirect: 'manual' });
    const altCookie = altResp.headers.get('set-cookie') || '';
    const altMatch = altCookie.match(/(^|;)\s*A3=([^;]+)/);
    if (!altMatch) throw new Error('Failed to get Yahoo cookie');
    _cache.cookie = `A3=${altMatch[2]}`;
  } else {
    _cache.cookie = `A3=${cookieMatch[2]}`;
  }

  // Step 2: Get crumb using cookie
  await sleep(500);
  const crumbResp = await fetch(YAHOO_CONFIG.crumbUrl, {
    headers: { Cookie: _cache.cookie },
  });
  if (!crumbResp.ok) throw new Error(`Failed to get crumb: ${crumbResp.status}`);
  _cache.crumb = (await crumbResp.text()).trim();
  _cache.expires = Date.now() + CACHE_TTL;

  return _cache;
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function matchProxy(urlPath, method) {
  for (const p of YAHOO_CONFIG.proxies) {
    if (urlPath.startsWith(p.path) && (!p.method || p.method === method)) {
      return p;
    }
  }
  return null;
}

export default {
  async fetch(request, env, ctx) {
    // Auth check
    const reqKey = request.headers.get('X-Proxy-Key');
    const expectedKey = env.WORKER_API_KEY || 'my-yahoo-proxy-key-2026';
    if (reqKey !== expectedKey) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const url = new URL(request.url);
    const targetUrl = url.searchParams.get('url');

    if (!targetUrl) {
      return new Response(JSON.stringify({ error: 'Missing url param' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const target = new URL(targetUrl);
    const path = target.pathname;
    const method = request.method;
    const proxy = matchProxy(path, method);

    if (!proxy) {
      return new Response(JSON.stringify({ error: 'Unsupported endpoint', path }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    try {
      // Ensure we have a valid crumb
      const auth = await ensureAuth();

      // Add crumb to query params for GET requests
      if (method === 'GET') {
        target.searchParams.set('crumb', auth.crumb);
        target.searchParams.set('corsDomain', 'finance.yahoo.com');
        target.searchParams.set('formatted', 'false');
      }

      // Build fetch options
      const fetchOpts = {
        method,
        headers: {
          'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
          'Cookie': auth.cookie,
        },
      };

      // Forward POST body
      if (method === 'POST') {
        const contentType = request.headers.get('content-type') || 'application/json';
        fetchOpts.headers['Content-Type'] = contentType;
        fetchOpts.body = request.body;
      }

      // Make request to Yahoo
      const yahooResp = await fetch(target.toString(), fetchOpts);
      const body = await yahooResp.text();

      return new Response(body, {
        status: yahooResp.status,
        headers: {
          'Content-Type': yahooResp.headers.get('Content-Type') || 'application/json',
          'Access-Control-Allow-Origin': '*',
        },
      });
    } catch (err) {
      // On auth failure, reset cache and retry once
      if (_cache.crumb) {
        _cache = { cookie: '', crumb: '', expires: 0 };
        try {
          return await fetch(request, env, ctx);
        } catch (_) {
          // Fall through
        }
      }
      return new Response(JSON.stringify({ error: err.message }), {
        status: 502,
        headers: { 'Content-Type': 'application/json' },
      });
    }
  },
};
