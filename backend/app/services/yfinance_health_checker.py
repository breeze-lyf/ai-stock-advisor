"""
Yahoo Finance 连接健康检查

负责定期探测 Yahoo Finance 直连是否可用，并在恢复时自动切换回直连模式。
"""
import logging
import asyncio
import httpx
from typing import Optional, Callable, Awaitable

logger = logging.getLogger(__name__)


class YFinanceHealthChecker:
    """
    YFinance 连接健康检查器

    功能：
    1. 定期探测 Yahoo Finance 直连是否可用
    2. 当直连恢复时，自动重置 YFinanceProvider 的代理标志
    3. 可配置探测间隔和超时时间
    """

    # 测试用的美股代码（高流动性，响应快）
    TEST_SYMBOL = "AAPL"

    # Yahoo Finance Chart API 端点
    YAHOO_CHART_URL = "https://query2.finance.yahoo.com/v8/finance/chart"

    # 默认配置
    DEFAULT_CHECK_INTERVAL = 300  # 5 分钟
    DEFAULT_TIMEOUT = 10.0  # 10 秒

    def __init__(
        self,
        check_interval: int = DEFAULT_CHECK_INTERVAL,
        timeout: float = DEFAULT_TIMEOUT,
        worker_url: Optional[str] = None,
        worker_key: Optional[str] = None
    ):
        self.check_interval = check_interval
        self.timeout = timeout
        self.worker_url = worker_url
        self.worker_key = worker_key
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._reset_callback: Optional[Callable[[], Awaitable[None]]] = None

    def set_reset_callback(self, callback: Callable[[], Awaitable[None]]) -> None:
        """设置代理重置回调函数"""
        self._reset_callback = callback

    async def check_yahoo_connectivity(self) -> bool:
        """
        检查 Yahoo Finance 直连是否可用

        Returns:
            bool: True 表示直连可用，False 表示需要通过代理
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.YAHOO_CHART_URL}/{self.TEST_SYMBOL}?interval=1d&range=1d"
                response = await client.get(url, follow_redirects=True)

                if response.status_code == 200:
                    data = response.json()
                    result = data.get("chart", {}).get("result", [])
                    if result:
                        logger.info("✓ Yahoo Finance 直连检测成功")
                        return True

                logger.warning(f"Yahoo Finance 直连检测失败：HTTP {response.status_code}")
                return False

        except httpx.TimeoutException:
            logger.warning("Yahoo Finance 直连检测超时")
            return False
        except Exception as e:
            logger.warning(f"Yahoo Finance 直连检测异常：{e}")
            return False

    async def check_worker_proxy(self) -> bool:
        """
        检查 Cloudflare Worker 代理是否可用

        Returns:
            bool: True 表示 Worker 代理可用
        """
        if not self.worker_url or not self.worker_key:
            return False

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                yahoo_url = f"{self.YAHOO_CHART_URL}/{self.TEST_SYMBOL}?interval=1d&range=1d"
                worker_request_url = f"{self.worker_url.rstrip('/')}/?url={httpx.URL(yahoo_url)}"

                response = await client.get(
                    worker_request_url,
                    headers={"X-Proxy-Key": self.worker_key},
                    follow_redirects=True,
                )

                if response.status_code == 200:
                    data = response.json()
                    result = data.get("chart", {}).get("result", [])
                    if result:
                        logger.info("✓ Cloudflare Worker 代理检测成功")
                        return True

                logger.warning(f"Cloudflare Worker 代理检测失败：HTTP {response.status_code}")
                return False

        except Exception as e:
            logger.warning(f"Cloudflare Worker 代理检测异常：{e}")
            return False

    async def run_check_and_reset(self) -> None:
        """
        执行一次健康检查，如果直连恢复则重置代理标志
        """
        logger.debug("Running Yahoo Finance health check...")

        # 检查直连是否恢复
        direct_ok = await self.check_yahoo_connectivity()

        if direct_ok and self._reset_callback:
            logger.info("Yahoo Finance 直连已恢复，重置代理标志")
            await self._reset_callback()

    async def start(self) -> None:
        """启动健康检查后台任务"""
        if self._running:
            logger.warning("YFinance health checker already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._check_loop())
        logger.info(f"YFinance health checker started (interval={self.check_interval}s)")

    async def stop(self) -> None:
        """停止健康检查后台任务"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("YFinance health checker stopped")

    async def _check_loop(self) -> None:
        """后台检查循环"""
        while self._running:
            try:
                await self.run_check_and_reset()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")

            # 等待下一次检查
            try:
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break


# 全局健康检查器实例
_health_checker: Optional[YFinanceHealthChecker] = None


def get_health_checker() -> Optional[YFinanceHealthChecker]:
    """获取全局健康检查器实例"""
    return _health_checker


def init_health_checker(
    check_interval: int = YFinanceHealthChecker.DEFAULT_CHECK_INTERVAL,
    timeout: float = YFinanceHealthChecker.DEFAULT_TIMEOUT,
    worker_url: Optional[str] = None,
    worker_key: Optional[str] = None
) -> YFinanceHealthChecker:
    """初始化全局健康检查器"""
    global _health_checker
    _health_checker = YFinanceHealthChecker(
        check_interval=check_interval,
        timeout=timeout,
        worker_url=worker_url,
        worker_key=worker_key
    )
    return _health_checker
