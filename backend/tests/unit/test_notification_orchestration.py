from __future__ import annotations

import os
from datetime import timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@127.0.0.1:5432/test_db")
os.environ.setdefault("SECRET_KEY", "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef")

from app.api.v1.endpoints.notifications import get_notification_history
from app.models.notification import NotificationLog
from app.models.notification_settings import UserNotificationSetting
from app.models.user import User
from app.services.notification_service_v2 import NotificationPriority, NotificationServiceV2
from app.core.database import Base


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=[
            User.__table__,
            UserNotificationSetting.__table__,
            NotificationLog.__table__,
        ])

    SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session

    await engine.dispose()


async def _create_user(
    db: AsyncSession,
    user_id: str,
    email: str,
    **kwargs,
) -> User:
    user = User(
        id=user_id,
        email=email,
        hashed_password="hashed",
        **kwargs,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.mark.asyncio
async def test_notification_history_is_user_scoped(db_session: AsyncSession):
    user_a = await _create_user(db_session, "u-1", "u1@example.com")
    await _create_user(db_session, "u-2", "u2@example.com")

    db_session.add_all(
        [
            NotificationLog(user_id="u-1", type="price_alert", title="A", content="mine", status="SUCCESS"),
            NotificationLog(user_id="u-2", type="price_alert", title="B", content="other", status="SUCCESS"),
        ]
    )
    await db_session.commit()

    history = await get_notification_history(limit=20, db=db_session, current_user=user_a)

    assert len(history) == 1
    assert history[0].user_id == "u-1"
    assert history[0].content == "mine"


@pytest.mark.asyncio
async def test_indicator_alert_respects_user_preference(monkeypatch, db_session: AsyncSession):
    await _create_user(
        db_session,
        "u-1",
        "u1@example.com",
        enable_indicator_alerts=False,
    )

    async def fake_feishu(**kwargs):
        return True

    monkeypatch.setattr(NotificationServiceV2, "_send_feishu", staticmethod(fake_feishu))

    result = await NotificationServiceV2.send_notification(
        db=db_session,
        user_id="u-1",
        title="Indicator",
        message="RSI",
        notification_type="indicator_alert",
        target_id="AAPL",
        semantic_key="rsi14:overbought",
    )

    assert result["blocked_reason"] == "enable_indicator_alerts_disabled"


@pytest.mark.asyncio
async def test_dedup_uses_notification_type_target_and_semantic_key(monkeypatch, db_session: AsyncSession):
    await _create_user(db_session, "u-1", "u1@example.com")

    async def fake_feishu(**kwargs):
        return True

    monkeypatch.setattr(NotificationServiceV2, "_send_feishu", staticmethod(fake_feishu))

    first = await NotificationServiceV2.send_notification(
        db=db_session,
        user_id="u-1",
        title="Price",
        message="Hit target",
        priority=NotificationPriority.P1,
        notification_type="price_alert",
        target_id="AAPL",
        semantic_key="take_profit:100.0000",
        dedupe_window=timedelta(hours=24),
    )
    duplicate = await NotificationServiceV2.send_notification(
        db=db_session,
        user_id="u-1",
        title="Price",
        message="Hit target",
        priority=NotificationPriority.P1,
        notification_type="price_alert",
        target_id="AAPL",
        semantic_key="take_profit:100.0000",
        dedupe_window=timedelta(hours=24),
    )
    second_semantic = await NotificationServiceV2.send_notification(
        db=db_session,
        user_id="u-1",
        title="Price",
        message="Hit higher target",
        priority=NotificationPriority.P1,
        notification_type="price_alert",
        target_id="AAPL",
        semantic_key="take_profit:105.0000",
        dedupe_window=timedelta(hours=24),
    )

    assert first["sent_channels"] == ["feishu"]
    assert duplicate["blocked_reason"] == "deduplicated"
    assert second_semantic["sent_channels"] == ["feishu"]

    logs = (await db_session.execute(
        NotificationLog.__table__.select().where(NotificationLog.user_id == "u-1")
    )).all()
    assert len(logs) == 2


@pytest.mark.asyncio
async def test_daily_limit_applies_to_unified_notification_flow(monkeypatch, db_session: AsyncSession):
    await _create_user(db_session, "u-1", "u1@example.com")
    setting = UserNotificationSetting(user_id="u-1", p2_daily_limit=1)
    db_session.add(setting)
    await db_session.commit()

    async def fake_feishu(**kwargs):
        return True

    monkeypatch.setattr(NotificationServiceV2, "_send_feishu", staticmethod(fake_feishu))

    first = await NotificationServiceV2.send_notification(
        db=db_session,
        user_id="u-1",
        title="Daily 1",
        message="report 1",
        priority=NotificationPriority.P2,
        notification_type="daily_report",
        target_id="daily_portfolio_report",
        semantic_key="2026-05-11",
        dedupe_window=timedelta(),
    )
    second = await NotificationServiceV2.send_notification(
        db=db_session,
        user_id="u-1",
        title="Daily 2",
        message="report 2",
        priority=NotificationPriority.P2,
        notification_type="daily_report",
        target_id="daily_portfolio_report",
        semantic_key="2026-05-12",
        dedupe_window=timedelta(),
    )

    assert first["sent_channels"] == ["feishu"]
    assert second["blocked_reason"] == "daily_limit_exceeded"
