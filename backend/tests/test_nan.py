import asyncio
import sys
import os
import math
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.analysis import AnalysisReport
from sqlalchemy import select

async def main():
    async with SessionLocal() as db:
        stmt = select(AnalysisReport)
        result = await db.execute(stmt)
        reports = result.scalars().all()
        
        for r in reports:
            for field in ['sentiment_score', 'confidence_level', 'target_price', 'stop_loss_price', 'entry_price_low', 'entry_price_high', 'max_drawdown', 'max_favorable_excursion']:
                val = getattr(r, field)
                if val is not None:
                    # if field is string like sentiment_score
                    if isinstance(val, str):
                        try:
                            f_val = float(val)
                            if math.isnan(f_val) or math.isinf(f_val):
                                print(f"Report {r.id} ({r.ticker}) has NaN/Inf in {field}: {val}")
                        except:
                            print(f"Report {r.id} ({r.ticker}) has non-floatable string in {field}: {val}")
                    elif isinstance(val, float):
                        if math.isnan(val) or math.isinf(val):
                            print(f"Report {r.id} ({r.ticker}) has NaN/Inf in {field}: {val}")

if __name__ == "__main__":
    asyncio.run(main())
