import asyncio
from app.core.database import SessionLocal, Base, engine
from app.models import User, Stock, Portfolio, AnalysisReport, AIModelConfig
from sqlalchemy.future import select

STOCKS_TO_SEED = [
    ("AAPL", "Apple Inc."),
    ("NVDA", "NVIDIA Corporation"),
    ("MSFT", "Microsoft Corporation"),
    ("GOOGL", "Alphabet Inc."),
    ("AMZN", "Amazon.com Inc."),
    ("META", "Meta Platforms Inc."),
    ("TSLA", "Tesla Inc."),
    ("BRK.B", "Berkshire Hathaway Inc."),
    ("LLY", "Eli Lilly and Company"),
    ("AVGO", "Broadcom Inc."),
    ("V", "Visa Inc."),
    ("JPM", "JPMorgan Chase & Co."),
    ("WMT", "Walmart Inc."),
    ("XOM", "Exxon Mobil Corporation"),
    ("MA", "Mastercard Incorporated"),
    ("UNH", "UnitedHealth Group Incorporated"),
    ("PG", "Procter & Gamble Company"),
    ("JNJ", "Johnson & Johnson"),
    ("HD", "The Home Depot Inc."),
    ("COST", "Costco Wholesale Corporation"),
    ("ABBV", "AbbVie Inc."),
    ("MRK", "Merck & Co. Inc."),
    ("ORCL", "Oracle Corporation"),
    ("KO", "The Coca-Cola Company"),
    ("BAC", "Bank of America Corporation"),
    ("CVX", "Chevron Corporation"),
    ("PEP", "PepsiCo Inc."),
    ("CRM", "Salesforce Inc."),
    ("AMD", "Advanced Micro Devices Inc."),
    ("NFLX", "Netflix Inc."),
    ("ACN", "Accenture plc"),
    ("LIN", "Linde plc"),
    ("MCD", "McDonald's Corporation"),
    ("TMO", "Thermo Fisher Scientific Inc."),
    ("ABT", "Abbott Laboratories"),
    ("CSCO", "Cisco Systems Inc."),
    ("INTC", "Intel Corporation"),
    ("WFC", "Wells Fargo & Company"),
    ("TMUS", "T-Mobile US Inc."),
    ("DIS", "The Walt Disney Company"),
    ("QCOM", "Qualcomm Incorporated"),
    ("DHR", "Danaher Corporation"),
    ("VZ", "Verizon Communications Inc."),
    ("IBM", "International Business Machines"),
    ("CAT", "Caterpillar Inc."),
    ("AXP", "American Express Company"),
    ("INTU", "Intuit Inc."),
    ("TXN", "Texas Instruments Incorporated"),
    ("AMGN", "Amgen Inc."),
    ("PFE", "Pfizer Inc.")
]


async def seed():
    async with engine.begin() as conn:
        print("🔧 Creating tables...")
        await conn.run_sync(Base.metadata.create_all)
        
    async with SessionLocal() as db:
        print("🌱 Seeding Stocks...")
        count = 0
        for ticker, name in STOCKS_TO_SEED:
            # Check if exists
            stmt = select(Stock).where(Stock.ticker == ticker)
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if not existing:
                stock = Stock(ticker=ticker, name=name)
                db.add(stock)
                count += 1
        
        await db.commit()
        print(f"✅ Added {count} new stocks.")

if __name__ == "__main__":
    asyncio.run(seed())
