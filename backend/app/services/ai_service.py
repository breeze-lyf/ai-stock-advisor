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
    async def generate_analysis(ticker: str, market_data: dict, portfolio_data: dict) -> str:
        AIService._configure_genai()
        
        if not settings.GEMINI_API_KEY:
             return f"# Analysis for {ticker} (Mock)\n\n> **Warning**: API Key missing.\n\nSimulated Request for {ticker}. Price: {market_data.get('current_price')}"

        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Construct Prompt
            prompt = f"""
            You are a senior investment advisor for a retail investor.
            Analyze the following stock based on the real-time data provided.
            
            **Target Stock**: {ticker}
            
            **Market Data**:
            - Current Price: ${market_data.get('current_price', 'N/A')}
            - Change: {market_data.get('change_percent', 0) * 100:.2f}%
            - RSI (14): {market_data.get('rsi_14', 'N/A')}
            - Status: {market_data.get('market_status', 'OPEN')}
            
            **User Position**:
            - Avg Cost: ${portfolio_data.get('avg_cost', 0)}
            - Quantity: {portfolio_data.get('quantity', 0)}
            - Unrealized P&L: ${portfolio_data.get('unrealized_pl', 0)} ({portfolio_data.get('pl_percent', 0):.2f}%)
            
            **Task**:
            1. **Status Diagnosis**: Briefly describe the technical status (Overbought/Oversold/Neutral).
            2. **Actionable Advice**: Should the user Buy, Sell, or Hold? Be specific based on their cost basis.
            3. **Risk Warning**: Mention one key risk (general volatility or specific if you know any news).
            
            **Format**:
            Use Markdown. Use Bold for key verdicts. Keep it concise (under 200 words).
            """
            
            response = await model.generate_content_async(prompt)
            return response.text

        except Exception as e:
            logger.error(f"Gemini API Error: {e}")
            return f"**Error**: Failed to generate analysis. {str(e)}"
