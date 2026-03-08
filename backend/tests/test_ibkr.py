"""
IBKR TWS 数据提供商集成测试
使用方法：
1. 确保 TWS 或 IB Gateway 已运行
2. 在 .env 中设置 IBKR_ENABLED=true
3. 运行: python tests/test_ibkr.py

注意：此测试需要真实的 IBKR 连接，不适合 CI/CD 环境。
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


async def test_connection():
    """测试 1: IBKR 连接"""
    print("\n" + "=" * 60)
    print("测试 1: IBKR 连接")
    print("=" * 60)

    from app.services.market_providers.ibkr import IBKRProvider
    provider = IBKRProvider()
    connected = await provider._ensure_connected()

    if connected:
        print("✅ 连接成功！")
    else:
        print("❌ 连接失败，请检查 TWS/IB Gateway 是否运行")
        return False
    return True


async def test_quote(ticker: str = "AAPL"):
    """测试 2: 获取实时报价"""
    print(f"\n{'=' * 60}")
    print(f"测试 2: 获取 {ticker} 实时报价")
    print("=" * 60)

    from app.services.market_providers.ibkr import IBKRProvider
    provider = IBKRProvider()
    quote = await provider.get_quote(ticker)

    if quote:
        print(f"✅ 报价获取成功:")
        print(f"   代码: {quote.ticker}")
        print(f"   价格: ${quote.price:.2f}")
        print(f"   涨跌幅: {quote.change_percent:+.2f}%")
        print(f"   市场状态: {quote.market_status}")
    else:
        print(f"❌ 未能获取 {ticker} 的报价")

    return quote


async def test_fundamental(ticker: str = "AAPL"):
    """测试 3: 获取基本面数据"""
    print(f"\n{'=' * 60}")
    print(f"测试 3: 获取 {ticker} 基本面数据")
    print("=" * 60)

    from app.services.market_providers.ibkr import IBKRProvider
    provider = IBKRProvider()
    fund = await provider.get_fundamental_data(ticker)

    if fund:
        print(f"✅ 基本面数据:")
        print(f"   PE: {fund.pe_ratio}")
        print(f"   EPS: {fund.eps}")
        print(f"   市值: {fund.market_cap}")
        print(f"   股息率: {fund.dividend_yield}")
        print(f"   52周高: {fund.fifty_two_week_high}")
        print(f"   52周低: {fund.fifty_two_week_low}")
    else:
        print(f"⚠️ 未获取到基本面数据（可能需要 Reuters 订阅）")

    return fund


async def test_historical(ticker: str = "AAPL"):
    """测试 4: 获取历史数据与技术指标"""
    print(f"\n{'=' * 60}")
    print(f"测试 4: 获取 {ticker} 历史数据与技术指标")
    print("=" * 60)

    from app.services.market_providers.ibkr import IBKRProvider
    provider = IBKRProvider()
    indicators = await provider.get_historical_data(ticker, period="200d")

    if indicators:
        print(f"✅ 技术指标计算成功:")
        for key, val in indicators.items():
            if val is not None:
                print(f"   {key}: {val}")
    else:
        print(f"❌ 未获取到历史数据")

    return indicators


async def test_ohlcv(ticker: str = "AAPL"):
    """测试 5: 获取 K 线数据"""
    print(f"\n{'=' * 60}")
    print(f"测试 5: 获取 {ticker} K 线数据 (OHLCV)")
    print("=" * 60)

    from app.services.market_providers.ibkr import IBKRProvider
    provider = IBKRProvider()
    data = await provider.get_ohlcv(ticker, period="1mo")

    if data:
        print(f"✅ K 线数据获取成功: {len(data)} 条")
        print(f"   最近一条: {data[-1].time} | O:{data[-1].open:.2f} H:{data[-1].high:.2f} L:{data[-1].low:.2f} C:{data[-1].close:.2f}")
    else:
        print(f"❌ 未获取到 K 线数据")

    return data


async def test_full_data(ticker: str = "AAPL"):
    """测试 6: 全量数据获取"""
    print(f"\n{'=' * 60}")
    print(f"测试 6: 获取 {ticker} 全量数据 (Full Data)")
    print("=" * 60)

    from app.services.market_providers.ibkr import IBKRProvider
    provider = IBKRProvider()
    full = await provider.get_full_data(ticker)

    if full:
        print(f"✅ 全量数据获取成功:")
        print(f"   报价: ${full.quote.price:.2f} ({full.quote.change_percent:+.2f}%)")
        if full.fundamental:
            print(f"   PE: {full.fundamental.pe_ratio}")
        if full.technical and full.technical.indicators:
            indicator_count = len(full.technical.indicators)
            print(f"   技术指标: {indicator_count} 个")
    else:
        print(f"❌ 全量数据获取失败")

    return full


async def test_factory_routing():
    """测试 7: 工厂路由逻辑"""
    print(f"\n{'=' * 60}")
    print(f"测试 7: 工厂路由逻辑")
    print("=" * 60)

    from app.services.market_providers.factory import ProviderFactory

    test_cases = [
        ("AAPL", "美股"),
        ("600519", "A 股"),
        ("0700.HK", "港股"),
        ("MSFT", "美股"),
    ]

    for ticker, market in test_cases:
        provider = ProviderFactory.get_provider(ticker)
        provider_name = type(provider).__name__
        print(f"   {ticker} ({market}) → {provider_name}")


async def main():
    """运行所有测试"""
    print("🚀 IBKR TWS 数据提供商集成测试")
    print("=" * 60)

    # 检查是否可用
    from app.services.market_providers.ibkr import IBKRProvider
    if not IBKRProvider.is_available():
        print("⚠️ IBKR 未启用。请在 .env 中设置 IBKR_ENABLED=true")
        print("   仅运行工厂路由测试...")
        await test_factory_routing()
        return

    # 连接测试
    connected = await test_connection()
    if not connected:
        print("\n⚠️ 无法连接 IBKR，跳过数据测试")
        await test_factory_routing()
        return

    ticker = "AAPL"
    if len(sys.argv) > 1:
        ticker = sys.argv[1]

    # 数据测试
    await test_quote(ticker)
    await test_fundamental(ticker)
    await test_historical(ticker)
    await test_ohlcv(ticker)
    await test_full_data(ticker)
    await test_factory_routing()

    # 断开连接
    provider = IBKRProvider()
    await provider.disconnect()

    print(f"\n{'=' * 60}")
    print("✅ 所有测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
