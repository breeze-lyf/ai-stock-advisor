"""
会员订阅 API
"""
from typing import Optional, List
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, func

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.subscription import SubscriptionPlan, UserSubscription, UsageRecord, PaymentTransaction

router = APIRouter()


@router.get("/subscription/plans")
async def list_subscription_plans(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取所有订阅计划"""
    stmt = select(SubscriptionPlan).where(
        SubscriptionPlan.is_active == True
    ).order_by(SubscriptionPlan.sort_order)

    result = await db.execute(stmt)
    plans = result.scalars().all()

    return {
        "status": "success",
        "plans": [
            {
                "id": p.id,
                "name": p.name,
                "name_zh": p.name_zh,
                "price_monthly": float(p.price_monthly),
                "price_yearly": float(p.price_yearly),
                "currency": p.currency,
                "daily_ai_analysis_limit": p.daily_ai_analysis_limit,
                "screener_conditions_limit": p.screener_conditions_limit,
                "backtest_history_months": p.backtest_history_months,
                "portfolio_stocks_limit": p.portfolio_stocks_limit,
                "data_refresh_delay_minutes": p.data_refresh_delay_minutes,
                "course_access": p.course_access,
                "description": p.description,
                "features": p.features,
            }
            for p in plans
        ],
    }


@router.get("/subscription/current")
async def get_current_subscription(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户当前订阅"""
    stmt = select(UserSubscription).where(
        and_(
            UserSubscription.user_id == current_user.id,
            UserSubscription.status == "ACTIVE"
        )
    )
    result = await db.execute(stmt)
    subscription = result.scalar_one_or_none()

    if not subscription:
        # 返回免费版默认信息
        return {
            "status": "success",
            "subscription": None,
            "plan": {
                "name": "FREE",
                "name_zh": "免费版",
                "daily_ai_analysis_limit": 3,
                "screener_conditions_limit": 3,
                "portfolio_stocks_limit": 10,
            },
        }

    return {
        "status": "success",
        "subscription": {
            "id": subscription.id,
            "status": subscription.status,
            "billing_cycle": subscription.billing_cycle,
            "current_period_start": subscription.current_period_start.isoformat(),
            "current_period_end": subscription.current_period_end.isoformat(),
            "trial_end": subscription.trial_end.isoformat() if subscription.trial_end else None,
            "cancelled_at": subscription.cancelled_at.isoformat() if subscription.cancelled_at else None,
        },
        "plan": {
            "name": subscription.plan.name,
            "name_zh": subscription.plan.name_zh,
            "daily_ai_analysis_limit": subscription.plan.daily_ai_analysis_limit,
            "screener_conditions_limit": subscription.plan.screener_conditions_limit,
            "portfolio_stocks_limit": subscription.plan.portfolio_stocks_limit,
            "backtest_history_months": subscription.plan.backtest_history_months,
            "data_refresh_delay_minutes": subscription.plan.data_refresh_delay_minutes,
            "course_access": subscription.plan.course_access,
        },
    }


@router.get("/subscription/usage")
async def get_usage_stats(
    days: int = Query(30, ge=1, le=90, description="查询天数"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户使用量统计"""
    start_date = date.today() - timedelta(days=days)

    stmt = select(UsageRecord).where(
        and_(
            UsageRecord.user_id == current_user.id,
            UsageRecord.usage_date >= start_date
        )
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    # 获取当前订阅的限制
    subscription_stmt = select(UserSubscription).where(
        and_(
            UserSubscription.user_id == current_user.id,
            UserSubscription.status == "ACTIVE"
        )
    )
    sub_result = await db.execute(subscription_stmt)
    subscription = sub_result.scalar_one_or_none()

    # 获取计划限制
    ai_limit = 3
    screener_limit = 3
    if subscription:
        plan_stmt = select(SubscriptionPlan).where(SubscriptionPlan.id == subscription.plan_id)
        plan_result = await db.execute(plan_stmt)
        plan = plan_result.scalar_one_or_none()
        if plan:
            ai_limit = plan.daily_ai_analysis_limit
            screener_limit = plan.screener_conditions_limit

    return {
        "status": "success",
        "period": {
            "start": start_date.isoformat(),
            "end": date.today().isoformat(),
        },
        "usage": [
            {
                "date": r.usage_date.isoformat(),
                "type": r.usage_type,
                "count": r.count,
                "limit": r.limit,
            }
            for r in records
        ],
        "limits": {
            "daily_ai_analysis": ai_limit,
            "screener_conditions": screener_limit,
        },
    }


@router.post("/subscription/trial")
async def start_trial(
    plan_id: str = Query(..., description="试用的计划 ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """开始试用（如果符合条件）"""
    # 检查用户是否已有订阅
    existing_stmt = select(UserSubscription).where(
        and_(
            UserSubscription.user_id == current_user.id,
            UserSubscription.status == "ACTIVE"
        )
    )
    existing_result = await db.execute(existing_stmt)
    existing = existing_result.scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=400, detail="Already have an active subscription")

    # 检查是否已使用过试用
    trial_stmt = select(UserSubscription).where(
        and_(
            UserSubscription.user_id == current_user.id,
            UserSubscription.trial_used == True
        )
    )
    trial_result = await db.execute(trial_stmt)
    trial_used = trial_result.scalar_one_or_none()

    if trial_used:
        raise HTTPException(status_code=400, detail="Trial already used")

    # 获取计划
    plan_stmt = select(SubscriptionPlan).where(
        and_(
            SubscriptionPlan.id == plan_id,
            SubscriptionPlan.is_active == True
        )
    )
    plan_result = await db.execute(plan_stmt)
    plan = plan_result.scalar_one_or_none()

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # 创建试用订阅（7 天试用）
    trial_start = date.today()
    trial_end = trial_start + timedelta(days=7)

    subscription = UserSubscription(
        user_id=current_user.id,
        plan_id=plan.id,
        status="TRIAL",
        billing_cycle="MONTHLY",
        current_period_start=trial_start,
        current_period_end=trial_end,
        trial_start=trial_start,
        trial_end=trial_end,
        trial_used=True,
    )
    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)

    return {
        "status": "success",
        "subscription": {
            "id": subscription.id,
            "plan_name": plan.name_zh,
            "trial_end": trial_end.isoformat(),
            "message": f"Trial started successfully. Ends on {trial_end.isoformat()}",
        },
    }


@router.post("/subscription/cancel")
async def cancel_subscription(
    reason: Optional[str] = Query(None, description="取消原因"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """取消订阅"""
    stmt = select(UserSubscription).where(
        and_(
            UserSubscription.user_id == current_user.id,
            UserSubscription.status == "ACTIVE"
        )
    )
    result = await db.execute(stmt)
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription found")

    subscription.status = "CANCELLED"
    subscription.cancelled_at = datetime.utcnow()
    subscription.cancel_reason = reason

    await db.commit()

    return {
        "status": "success",
        "message": "Subscription cancelled successfully",
        "access_until": subscription.current_period_end.isoformat(),
    }


@router.get("/subscription/transactions")
async def get_transactions(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取支付记录"""
    stmt = select(PaymentTransaction).where(
        PaymentTransaction.user_id == current_user.id
    ).order_by(PaymentTransaction.created_at.desc()).limit(limit)

    result = await db.execute(stmt)
    transactions = result.scalars().all()

    return {
        "status": "success",
        "count": len(transactions),
        "transactions": [
            {
                "id": t.id,
                "transaction_type": t.transaction_type,
                "amount": float(t.amount),
                "currency": t.currency,
                "status": t.status,
                "payment_provider": t.payment_provider,
                "paid_at": t.paid_at.isoformat() if t.paid_at else None,
                "invoice_url": t.invoice_url,
            }
            for t in transactions
        ],
    }
