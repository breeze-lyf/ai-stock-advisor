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
    async def generate_analysis(ticker: str, market_data: dict, portfolio_data: dict, api_key: str = None) -> str:
        # 1. Determine Key
        gemini_key = api_key or settings.GEMINI_API_KEY
        
        if not gemini_key:
             return f"# Analysis for {ticker} (Mock)\n\n> **Warning**: API Key missing. Please set it in Settings."
        
        # 2. Configure
        genai.configure(api_key=gemini_key)

        try:
            # 3. Define Tools (MCP)
            tools = [AIService._tool_get_stock_price]
            
            # 4. Initialize Model with Tools
            model = genai.GenerativeModel(
                model_name='gemini-1.5-flash',
                tools=tools
            )
            
            # 5. Start Chat Session (Automatic Function Calling)
            chat = model.start_chat(enable_automatic_function_calling=True)
            
            # 6. Prompt
            prompt = f"""
            You are a senior investment advisor.
            
            **User Portfolio Context**:
            - Ticker: {ticker}
            - Avg Cost: ${portfolio_data.get('avg_cost', 0)}
            - Quantity: {portfolio_data.get('quantity', 0)}
            - Unrealized P&L: ${portfolio_data.get('unrealized_pl', 0)}
            
            **Task**:
            1. Use the `get_stock_price` tool to fetch the latest data for {ticker}.
            2. Analyze the stock's status.
            3. Give Buy/Sell/Hold advice based on the User's Cost Basis vs Current Price.
            
            **CRITICAL**: Return the result purely as a JSON Object with NO Markdown formatting.
            Structure:
            {{
                "technical_analysis": "Summary of price action, RSI, and trends.",
                "fundamental_news": "Any known fundamental drivers or news (if unknown, state 'No recent major news').",
                "action_advice": "Specific recommendation (Buy/Sell/Hold) and logic."
            }}
            """
            
            # Use generation_config to force JSON (if supported by sdk version, else we rely on prompt)
            # For this MVP environment version, relying on prompt text is safer if types unknown.
            # But the 'response_mime_type' is the modern way.
            try:
                response = await chat.send_message_async(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
            except Exception:
                # Fallback if config fails
                 response = await chat.send_message_async(prompt)

            return response.text

        except Exception as e:
            logger.error(f"Gemini API Error: {e}")
            return f"**Error**: Failed to generate analysis. {str(e)}"
