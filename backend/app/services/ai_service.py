import google.generativeai as genai
from app.core.config import settings
import logging

# Configure Logging
logger = logging.getLogger(__name__)

class AIService:
    _configured = False

    @classmethod
    def _configure_genai(cls):
        if not cls._configured:
            if settings.GEMINI_API_KEY:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                cls._configured = True
            else:
                logger.warning("GEMINI_API_KEY not found. AI features will be disabled/mocked.")

    @staticmethod
    def _tool_get_stock_price(ticker: str):
        """
        Fetches the real-time stock price and data for a given ticker symbol.
        
        Args:
            ticker: The stock ticker symbol (e.g., 'AAPL', 'NVDA').
        """
        import yfinance as yf
        try:
            tick = yf.Ticker(ticker)
            info = tick.info
            context = {
                "price": info.get('currentPrice', info.get('regularMarketPrice')),
                "change_percent": info.get('regularMarketChangePercent', 0) * 100,
                "pe_ratio": info.get('trailingPE'),
                "market_cap": info.get('marketCap')
            }
            return context
        except Exception:
            return {"error": "Failed to fetch data"}

    @staticmethod
    async def generate_analysis(ticker: str, market_data: dict, portfolio_data: dict, news_data: list = None, api_key: str = None) -> str:
        # 1. Determine Key
        gemini_key = api_key or settings.GEMINI_API_KEY
        
        if not gemini_key:
             return f"# Analysis for {ticker} (Mock)\n\n> **Warning**: API Key missing. Please set it in Settings."
        
        # 2. Configure
        genai.configure(api_key=gemini_key)

        try:
            # 3. Initialize Model (Using full path for stability)
            model = genai.GenerativeModel(model_name='models/gemini-1.5-flash')
            
            # 4. Prompt Engineering (Already in Chinese)
            prompt = f"""
            你是一位资深美股投资顾问。
            
            **用户持仓背景 (Portfolio Context)**:
            - 代码: {ticker}
            - 成本价: ${portfolio_data.get('avg_cost', 0)}
            - 持仓数量: {portfolio_data.get('quantity', 0)}
            - 未实现盈亏: ${portfolio_data.get('unrealized_pl', 0)}
            
            **实时技术面数据 (Technical Data)**:
            - 当前价格: ${market_data.get('current_price')}
            - 今日涨跌: {market_data.get('change_percent')}%
            - RSI (14): {market_data.get('rsi_14')}
            - MACD: {market_data.get('macd_val')} (柱状图: {market_data.get('macd_hist')})
            - 布林带: [{market_data.get('bb_lower')}, {market_data.get('bb_upper')}]
            - KDJ (K): {market_data.get('kdj_k')}
            - ATR: {market_data.get('atr_14')}
            
            **最新消息面 (Recent News)**:
            {news_data if news_data else "暂无重大相关新闻。"}
            
            **任务 (Task)**:
            1. 综合分析：结合技术指标（趋势、波动、震荡）和最新的消息面，判断当前股价处于什么状态（底部反转、高位调整、强势拉升等）。
            2. 消息面影响：解读最新的新闻对股价是利好还是利空，是否支撑当前的技术走势。
            3. 操作建议：根据用户的持仓成本，给出具体的 [买入/卖出/持有] 建议，并说明理由。
            
            **要求**:
            - 使用中文回答。
            - 必须严格返回如下 JSON 格式，且不要包含任何 Markdown 代码块标签（如 ```json）。
            
            结果结构:
            {{
                "technical_analysis": "（技术面深度总结，包含对收盘价与均线/布林带关系的解读）",
                "fundamental_news": "（消息面解读，将最近新闻与公司基本面结合）",
                "action_advice": "（给用户的具体操作建议及风控点）"
            }}
            """
            
            # 5. Generate content directly
            response = await model.generate_content_async(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            return response.text

        except Exception as e:
            logger.error(f"Gemini API Error: {str(e)}")
            # Fallback simple generation if JSON mode fails
            try:
                model_alt = genai.GenerativeModel(model_name='models/gemini-1.5-flash')
                resp = await model_alt.generate_content_async(prompt)
                return resp.text
            except Exception as final_e:
                return f"**Error**: AI 分析失败。详细信息: {str(final_e)}"
