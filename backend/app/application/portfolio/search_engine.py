from __future__ import annotations

from app.application.portfolio.search_helpers import build_provider_order, build_search_candidates
from app.infrastructure.db.repositories.stock_repository import StockRepository
from app.schemas.portfolio import SearchResult
from app.services.market_providers import ProviderFactory


class PortfolioSearchEngine:
    def __init__(self, repo: StockRepository):
        self.repo = repo

    async def search(
        self,
        query: str,
        *,
        preferred_source: str | None,
        remote: bool,
        limit: int = 10,
    ) -> list[SearchResult]:
        normalized = (query or "").strip().upper()
        if not normalized:
            return []

        local_stocks = await self.repo.search(query, limit=limit)
        results = [SearchResult(ticker=s.ticker, name=s.name) for s in local_stocks]
        seen = {item.ticker.upper() for item in results}
        search_candidates = build_search_candidates(normalized)

        if not remote:
            return results

        exact_match = any(item.ticker.upper() in search_candidates for item in results)
        for source in build_provider_order(preferred_source, query):
            provider = ProviderFactory.get_provider(normalized, preferred_source=source)

            if not exact_match:
                for candidate in search_candidates:
                    quote = await provider.get_quote(candidate)
                    if not quote:
                        continue

                    resolved_ticker = (quote.ticker or candidate).upper()
                    await self._ensure_stock(resolved_ticker, quote.name or resolved_ticker, quote.price)
                    if resolved_ticker not in seen:
                        results.append(SearchResult(ticker=resolved_ticker, name=quote.name or resolved_ticker))
                        seen.add(resolved_ticker)
                    exact_match = True
                    break

            search_instruments = getattr(provider, "search_instruments", None)
            if callable(search_instruments):
                remote_results = await search_instruments(query, limit=limit)
                for item in remote_results:
                    ticker = str(item.get("ticker") or "").strip().upper()
                    name = str(item.get("name") or ticker).strip() or ticker
                    if not ticker or ticker in seen:
                        continue
                    await self._ensure_stock(ticker, name)
                    results.append(SearchResult(ticker=ticker, name=name))
                    seen.add(ticker)
                    if len(results) >= limit:
                        return results

            if len(results) >= limit:
                break

        return results[:limit]

    async def _ensure_stock(self, ticker: str, name: str, current_price: float | None = None) -> None:
        existing_stock = await self.repo.get_stock(ticker)
        if existing_stock:
            return
        await self.repo.add_stock_with_cache(ticker, name, current_price)
