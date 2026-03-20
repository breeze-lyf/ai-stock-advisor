import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.core.database import SessionLocal
from app.models.analysis import AnalysisReport
from sqlalchemy import select

async def main():
    async with SessionLocal() as db:
        stmt = select(AnalysisReport)
        result = await db.execute(stmt)
        reports = result.scalars().all()
        
        for r in reports:
            snapshot = r.input_context_snapshot or {}
            if isinstance(snapshot, str):
                print(f"Report {r.id} ({r.ticker}) has string snapshot! Error reproduces!")

if __name__ == "__main__":
    asyncio.run(main())
