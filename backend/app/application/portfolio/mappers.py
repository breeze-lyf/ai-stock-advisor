from app.schemas.portfolio import PortfolioItem, PortfolioSummary, SectorExposure


def portfolio_item_from_row(portfolio, market_cache, stock) -> PortfolioItem:
    current_price = market_cache.current_price if market_cache else 0.0
    market_value = current_price * portfolio.quantity
    unrealized_pl = (current_price - portfolio.avg_cost) * portfolio.quantity
    pl_percent = (
        (unrealized_pl / (portfolio.avg_cost * portfolio.quantity)) * 100
        if (portfolio.avg_cost > 0 and portfolio.quantity > 0)
        else 0
    )

    return PortfolioItem(
        ticker=portfolio.ticker,
        name=stock.name if stock else portfolio.ticker,
        quantity=portfolio.quantity,
        avg_cost=portfolio.avg_cost,
        current_price=current_price,
        market_value=market_value,
        unrealized_pl=unrealized_pl,
        pl_percent=pl_percent,
        last_updated=market_cache.last_updated if market_cache else None,
        sector=stock.sector if stock else None,
        industry=getattr(stock, "industry", None) if stock else None,
        market_cap=getattr(stock, "market_cap", None) if stock else None,
        pe_ratio=getattr(stock, "pe_ratio", None) if stock else None,
        forward_pe=getattr(stock, "forward_pe", None) if stock else None,
        eps=getattr(stock, "eps", None) if stock else None,
        dividend_yield=getattr(stock, "dividend_yield", None) if stock else None,
        beta=getattr(stock, "beta", None) if stock else None,
        fifty_two_week_high=getattr(stock, "fifty_two_week_high", None) if stock else None,
        fifty_two_week_low=getattr(stock, "fifty_two_week_low", None) if stock else None,
        pe_percentile=getattr(market_cache, "pe_percentile", None) if market_cache else None,
        pb_percentile=getattr(market_cache, "pb_percentile", None) if market_cache else None,
        net_inflow=getattr(market_cache, "net_inflow", None) if market_cache else None,
        rsi_14=getattr(market_cache, "rsi_14", None) if market_cache else None,
        ma_20=getattr(market_cache, "ma_20", None) if market_cache else None,
        ma_50=getattr(market_cache, "ma_50", None) if market_cache else None,
        ma_200=getattr(market_cache, "ma_200", None) if market_cache else None,
        macd_val=getattr(market_cache, "macd_val", None) if market_cache else None,
        macd_signal=getattr(market_cache, "macd_signal", None) if market_cache else None,
        macd_hist=getattr(market_cache, "macd_hist", None) if market_cache else None,
        macd_hist_slope=getattr(market_cache, "macd_hist_slope", None) if market_cache else None,
        macd_cross=getattr(market_cache, "macd_cross", None) if market_cache else None,
        macd_is_new_cross=bool(getattr(market_cache, "macd_is_new_cross", False)) if market_cache else False,
        bb_upper=getattr(market_cache, "bb_upper", None) if market_cache else None,
        bb_middle=getattr(market_cache, "bb_middle", None) if market_cache else None,
        bb_lower=getattr(market_cache, "bb_lower", None) if market_cache else None,
        atr_14=getattr(market_cache, "atr_14", None) if market_cache else None,
        k_line=getattr(market_cache, "k_line", None) if market_cache else None,
        d_line=getattr(market_cache, "d_line", None) if market_cache else None,
        j_line=getattr(market_cache, "j_line", None) if market_cache else None,
        volume_ma_20=getattr(market_cache, "volume_ma_20", None) if market_cache else None,
        volume_ratio=getattr(market_cache, "volume_ratio", None) if market_cache else None,
        adx_14=getattr(market_cache, "adx_14", None) if market_cache else None,
        pivot_point=getattr(market_cache, "pivot_point", None) if market_cache else None,
        resistance_1=getattr(market_cache, "resistance_1", None) if market_cache else None,
        resistance_2=getattr(market_cache, "resistance_2", None) if market_cache else None,
        support_1=getattr(market_cache, "support_1", None) if market_cache else None,
        support_2=getattr(market_cache, "support_2", None) if market_cache else None,
        risk_reward_ratio=getattr(market_cache, "risk_reward_ratio", None) if market_cache else None,
        change_percent=getattr(market_cache, "change_percent", 0.0) if market_cache else 0.0,
    )


def portfolio_summary_from_rows(rows) -> PortfolioSummary:
    holdings = []
    total_market_value = 0.0
    total_unrealized_pl = 0.0
    total_cost = 0.0
    total_day_change = 0.0
    sector_data: dict[str, float] = {}

    for portfolio, market_cache, stock in rows:
        item = portfolio_item_from_row(portfolio, market_cache, stock)
        holdings.append(item)

        total_market_value += item.market_value
        total_unrealized_pl += item.unrealized_pl
        total_cost += portfolio.avg_cost * portfolio.quantity

        if market_cache and market_cache.change_percent:
            day_chg_ratio = market_cache.change_percent / 100
            total_day_change += item.market_value * (day_chg_ratio / (1 + day_chg_ratio))

        sector = item.sector or "Unknown"
        sector_data[sector] = sector_data.get(sector, 0.0) + item.market_value

    sector_exposure = []
    for sector, value in sector_data.items():
        weight = (value / total_market_value * 100) if total_market_value > 0 else 0
        sector_exposure.append(SectorExposure(sector=sector, weight=weight, value=value))

    total_pl_percent = (total_unrealized_pl / total_cost * 100) if total_cost > 0 else 0

    return PortfolioSummary(
        total_market_value=total_market_value,
        total_unrealized_pl=total_unrealized_pl,
        total_pl_percent=total_pl_percent,
        day_change=total_day_change,
        holdings=holdings,
        sector_exposure=sector_exposure,
    )
