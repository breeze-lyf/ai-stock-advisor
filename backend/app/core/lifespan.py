"""
Application lifespan: startup/shutdown hooks, compatibility patches, proxy checks.
"""
import asyncio
import logging
import os
import socket
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import FastAPI

from app.core.config import settings

logger = logging.getLogger(__name__)


def _patch_py_mini_racer_cleanup_bug() -> None:
    """
    兼容补丁：py_mini_racer 在 Python 3.14 下可能在解释器回收期触发 __del__ 空指针。
    """
    try:
        from py_mini_racer.py_mini_racer import MiniRacer
    except Exception:
        return

    if getattr(MiniRacer, "_safe_del_patched", False):
        return

    def _safe_del(self):
        try:
            ext = getattr(self, "ext", None)
            if ext is None:
                return
            free_ctx = getattr(ext, "mr_free_context", None)
            if callable(free_ctx):
                free_ctx(getattr(self, "ctx", None))
        except Exception:
            pass

    MiniRacer.__del__ = _safe_del  # type: ignore[method-assign]
    MiniRacer._safe_del_patched = True  # type: ignore[attr-defined]


def _patch_httpx_asyncclient_compat() -> None:
    """
    兼容补丁：部分第三方 SDK 仍依赖旧版 httpx AsyncClient 行为。
    """
    try:
        import inspect
        import httpx
    except Exception:
        return

    async_client_cls = httpx.AsyncClient
    if getattr(async_client_cls, "_compat_init_patched", False):
        return

    original_init = async_client_cls.__init__
    accepts_proxies = "proxies" in inspect.signature(original_init).parameters

    def _compat_init(self, *args, **kwargs):
        if "proxies" in kwargs and "proxy" not in kwargs and not accepts_proxies:
            raw_proxies = kwargs.pop("proxies")
            if isinstance(raw_proxies, dict):
                proxy_val = (
                    raw_proxies.get("https://")
                    or raw_proxies.get("http://")
                    or raw_proxies.get("https")
                    or raw_proxies.get("http")
                )
            else:
                proxy_val = raw_proxies
            kwargs["proxy"] = proxy_val
        limits = kwargs.get("limits")
        original_init(self, *args, **kwargs)
        if not hasattr(self, "_limits"):
            self._limits = limits

    async_client_cls.__init__ = _compat_init  # type: ignore[method-assign]
    async_client_cls._compat_init_patched = True  # type: ignore[attr-defined]


def _is_proxy_reachable(proxy_url: str, timeout: float = 0.4) -> bool:
    try:
        parsed = urlparse(proxy_url)
        host = parsed.hostname
        port = parsed.port
        if not host or not port:
            return False
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def _normalize_proxy_env() -> None:
    """启动时检查代理连通性，不可达时自动清理环境变量。"""
    http_proxy = getattr(settings, "HTTP_PROXY", None)
    https_proxy = getattr(settings, "HTTPS_PROXY", None) or http_proxy
    no_proxy = getattr(settings, "NO_PROXY", None)

    if http_proxy:
        os.environ.setdefault("HTTP_PROXY", http_proxy)
        os.environ.setdefault("http_proxy", http_proxy)
    if https_proxy:
        os.environ.setdefault("HTTPS_PROXY", https_proxy)
        os.environ.setdefault("https_proxy", https_proxy)
    if no_proxy:
        os.environ.setdefault("NO_PROXY", no_proxy)
        os.environ.setdefault("no_proxy", no_proxy)

    if (http_proxy or https_proxy) and getattr(settings, "AKSHARE_BYPASS_PROXY", True):
        akshare_domains = [
            "push2.eastmoney.com",
            "push2his.eastmoney.com",
            "push2ex.eastmoney.com",
            "datacenter-web.eastmoney.com",
            "data.eastmoney.com",
            "stock.gtimg.cn",
            "hq.sinajs.cn",
            "money.finance.sina.com.cn",
            "*.eastmoney.com",
            "*.sinajs.cn",
            "*.gtimg.cn",
        ]
        existing = os.environ.get("NO_PROXY", "") or os.environ.get("no_proxy", "")
        existing_set = {d.strip() for d in existing.split(",") if d.strip()}
        merged = existing_set | set(akshare_domains)
        no_proxy_value = ",".join(sorted(merged))
        os.environ["NO_PROXY"] = no_proxy_value
        os.environ["no_proxy"] = no_proxy_value
        logger.info(f"AkShare bypass: added domestic domains to NO_PROXY ({len(akshare_domains)} domains)")

    if not getattr(settings, "AUTO_DISABLE_UNAVAILABLE_PROXY", True):
        return

    candidates = [p for p in [http_proxy, https_proxy] if p]
    if not candidates:
        return

    if any(_is_proxy_reachable(proxy) for proxy in candidates):
        logger.info("Proxy detected and reachable. Keeping proxy settings.")
        return

    for var in [
        "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
        "http_proxy", "https_proxy", "all_proxy",
        "NO_PROXY", "no_proxy"
    ]:
        os.environ.pop(var, None)
    logger.warning("Configured proxy is unreachable. Cleared proxy env vars for this process.")


# 尽早应用兼容补丁
_patch_httpx_asyncclient_compat()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _patch_py_mini_racer_cleanup_bug()
    _patch_httpx_asyncclient_compat()
    _normalize_proxy_env()

    from app.core.database import SessionLocal
    from app.services.integrations.ai.system_ai_registry import ensure_system_ai_registry
    from app.services.scheduler.scheduler import start_scheduler

    async with SessionLocal() as db:
        await ensure_system_ai_registry(db)

    scheduler_task = asyncio.create_task(start_scheduler())
    app.state.scheduler_task = scheduler_task
    logger.info("PHASE: Background scheduler task launched & DB synced.")

    from app.websocket.manager import websocket_manager
    await websocket_manager.start()

    try:
        yield
    finally:
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            logger.info("PHASE: Background scheduler task cancelled.")

        from app.websocket.manager import websocket_manager
        await websocket_manager.stop()

        await health_checker.stop()

        from app.core.redis_client import close_redis
        await close_redis()
