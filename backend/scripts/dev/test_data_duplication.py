import asyncio
import logging

from app.services.market_providers.akshare import AkShareProvider

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_duplication():
    provider = AkShareProvider()
    symbols = ["AAPL", "NVDA", "000001.SZ", "600519.SH"]

    for symbol in symbols:
        logger.info("Testing %s...", symbol)
        df = await provider.get_ohlcv(symbol)
        if not df:
            continue

        times = [item.time for item in df]
        if len(times) != len(set(times)):
            logger.error("Found duplicate timestamps in get_ohlcv output for %s", symbol)
        else:
            logger.info("get_ohlcv output for %s is clean", symbol)

        is_sorted = all(times[i] <= times[i + 1] for i in range(len(times) - 1))
        if not is_sorted:
            logger.error("Timestamps in get_ohlcv output for %s are NOT sorted", symbol)
        else:
            logger.info("Timestamps in get_ohlcv output for %s are sorted", symbol)


if __name__ == "__main__":
    asyncio.run(test_duplication())
