#!/usr/bin/env python3
"""
Seed script: insert 2025-2026 FOMC meeting dates into economic_events table.

Run from project root:
    source .venv/bin/activate
    cd backend
    python -m scripts.oneoff.seed_fomc_dates
"""
import asyncio
import sys
import os
import uuid
from datetime import date

# Allow running as a module from the backend directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sqlalchemy import select
from app.core.database import SessionLocal
# Import all models to resolve SQLAlchemy relationship mappings
import app.models  # noqa: F401 - triggers __init__ model registration
from app.models.calendar import EconomicEvent

# Federal Reserve FOMC meeting dates (statement release day)
# Source: federalreserve.gov/monetarypolicy/fomccalendars.htm
FOMC_DATES: list[tuple[date, str]] = [
    # 2025
    (date(2025, 1, 29), "2025年1月 FOMC 利率决议"),
    (date(2025, 3, 19), "2025年3月 FOMC 利率决议"),
    (date(2025, 5, 7),  "2025年5月 FOMC 利率决议"),
    (date(2025, 6, 18), "2025年6月 FOMC 利率决议"),
    (date(2025, 7, 30), "2025年7月 FOMC 利率决议"),
    (date(2025, 9, 17), "2025年9月 FOMC 利率决议"),
    (date(2025, 10, 29), "2025年10月 FOMC 利率决议"),
    (date(2025, 12, 17), "2025年12月 FOMC 利率决议"),
    # 2026
    (date(2026, 1, 28), "2026年1月 FOMC 利率决议"),
    (date(2026, 3, 18), "2026年3月 FOMC 利率决议"),
    (date(2026, 4, 29), "2026年4月 FOMC 利率决议"),
    (date(2026, 6, 17), "2026年6月 FOMC 利率决议"),
    (date(2026, 7, 29), "2026年7月 FOMC 利率决议"),
    (date(2026, 9, 16), "2026年9月 FOMC 利率决议"),
    (date(2026, 10, 28), "2026年10月 FOMC 利率决议"),
    (date(2026, 12, 16), "2026年12月 FOMC 利率决议"),
]


async def seed_fomc() -> None:
    async with SessionLocal() as db:
        inserted = 0
        skipped = 0

        for event_date, title in FOMC_DATES:
            # Check if already exists
            stmt = select(EconomicEvent).where(
                EconomicEvent.event_date == event_date,
                EconomicEvent.event_type == "FOMC",
            )
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                skipped += 1
                continue

            event = EconomicEvent(
                id=str(uuid.uuid4()),
                title=title,
                description="美联储联邦公开市场委员会利率决议，公布联邦基金目标利率调整结果及政策声明",
                event_type="FOMC",
                event_date=event_date,
                event_time="14:00",
                timezone="America/New_York",
                country="US",
                region="Federal Reserve",
                importance=3,  # 最高重要性
                source="federalreserve.gov",
                affected_sectors='["Technology","Finance","Real Estate","Consumer Discretionary"]',
            )
            db.add(event)
            inserted += 1

        await db.commit()
        print(f"FOMC seed complete: {inserted} inserted, {skipped} already existed.")


if __name__ == "__main__":
    asyncio.run(seed_fomc())
