"""
系统监控 API
提供系统健康检查、错误日志查询等功能
"""
from typing import Optional, List
from datetime import datetime, timedelta, date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, func, desc

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.monitoring import APIMetric, ErrorLog, SystemHealthCheck, AlertRule, AlertHistory

router = APIRouter()


@router.get("/monitoring/health")
async def get_system_health(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取系统健康状态"""
    # 获取最近一次健康检查
    stmt = select(SystemHealthCheck).order_by(desc(SystemHealthCheck.checked_at)).limit(1)
    result = await db.execute(stmt)
    latest_check = result.scalar_one_or_none()

    if not latest_check:
        return {
            "status": "success",
            "health": {
                "overall_status": "UNKNOWN",
                "message": "No health check data available",
            },
        }

    return {
        "status": "success",
        "health": {
            "overall_status": latest_check.overall_status,
            "database_status": latest_check.database_status,
            "redis_status": latest_check.redis_status,
            "ai_provider_status": latest_check.ai_provider_status,
            "notification_status": latest_check.notification_status,
            "active_connections": latest_check.active_connections,
            "avg_response_time_ms": float(latest_check.avg_response_time_ms) if latest_check.avg_response_time_ms else None,
            "error_rate_percent": float(latest_check.error_rate_percent) if latest_check.error_rate_percent else None,
            "checked_at": latest_check.checked_at.isoformat(),
            "details": latest_check.details,
        },
    }


@router.get("/monitoring/metrics")
async def get_api_metrics(
    days: int = Query(7, ge=1, le=30, description="查询天数"),
    endpoint: Optional[str] = Query(None, description="API 端点"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取 API 性能指标"""
    start_date = date.today() - timedelta(days=days)

    conditions = [APIMetric.request_date >= start_date]

    if endpoint:
        conditions.append(APIMetric.endpoint.like(f"%{endpoint}%"))

    # 聚合统计
    stmt = select(
        APIMetric.endpoint,
        func.count(APIMetric.id).label("total_requests"),
        func.avg(APIMetric.response_time_ms).label("avg_response_time"),
        func.max(APIMetric.response_time_ms).label("max_response_time"),
        func.sum(func.case((APIMetric.status_code >= 400, 1), else_=0)).label("error_count"),
    ).where(and_(*conditions)).group_by(APIMetric.endpoint).order_by(desc("total_requests")).limit(50)

    result = await db.execute(stmt)
    rows = result.fetchall()

    return {
        "status": "success",
        "period": {
            "start": start_date.isoformat(),
            "end": date.today().isoformat(),
        },
        "metrics": [
            {
                "endpoint": row.endpoint,
                "total_requests": row.total_requests,
                "avg_response_time_ms": round(float(row.avg_response_time), 2) if row.avg_response_time else 0,
                "max_response_time_ms": round(float(row.max_response_time), 2) if row.max_response_time else 0,
                "error_count": row.error_count,
                "error_rate_percent": round((row.error_count / row.total_requests * 100), 2) if row.total_requests > 0 else 0,
            }
            for row in rows
        ],
    }


@router.get("/monitoring/errors")
async def get_error_logs(
    days: int = Query(7, ge=1, le=30, description="查询天数"),
    endpoint: Optional[str] = Query(None, description="API 端点"),
    error_type: Optional[str] = Query(None, description="错误类型"),
    resolved: Optional[bool] = Query(None, description="是否已解决"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取错误日志"""
    start_date = date.today() - timedelta(days=days)

    conditions = [ErrorLog.created_at >= start_date]

    if endpoint:
        conditions.append(ErrorLog.endpoint.like(f"%{endpoint}%"))
    if error_type:
        conditions.append(ErrorLog.error_type == error_type)
    if resolved is not None:
        conditions.append(ErrorLog.resolved == resolved)

    stmt = select(ErrorLog).where(and_(*conditions)).order_by(desc(ErrorLog.created_at)).limit(limit)
    result = await db.execute(stmt)
    errors = result.scalars().all()

    return {
        "status": "success",
        "count": len(errors),
        "errors": [
            {
                "id": e.id,
                "endpoint": e.endpoint,
                "method": e.method,
                "error_type": e.error_type,
                "error_message": e.error_message,
                "status_code": e.status_code,
                "user_id": e.user_id,
                "resolved": e.resolved,
                "created_at": e.created_at.isoformat(),
            }
            for e in errors
        ],
    }


@router.get("/monitoring/errors/{error_id}")
async def get_error_detail(
    error_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取错误详情"""
    stmt = select(ErrorLog).where(ErrorLog.id == error_id)
    result = await db.execute(stmt)
    error = result.scalar_one_or_none()

    if not error:
        raise HTTPException(status_code=404, detail="Error log not found")

    return {
        "status": "success",
        "error": {
            "id": error.id,
            "endpoint": error.endpoint,
            "method": error.method,
            "error_type": error.error_type,
            "error_message": error.error_message,
            "stack_trace": error.stack_trace,
            "status_code": error.status_code,
            "request_body": error.request_body,
            "user_agent": error.user_agent,
            "client_ip": error.client_ip,
            "user_id": error.user_id,
            "resolved": error.resolved,
            "resolved_at": error.resolved_at.isoformat() if error.resolved_at else None,
            "resolved_by": error.resolved_by,
            "created_at": error.created_at.isoformat(),
        },
    }


@router.post("/monitoring/errors/{error_id}/resolve")
async def resolve_error(
    error_id: str,
    notes: Optional[str] = Query(None, description="解决说明"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """标记错误为已解决"""
    stmt = select(ErrorLog).where(ErrorLog.id == error_id)
    result = await db.execute(stmt)
    error = result.scalar_one_or_none()

    if not error:
        raise HTTPException(status_code=404, detail="Error log not found")

    error.resolved = True
    error.resolved_at = datetime.utcnow()
    error.resolved_by = current_user.id
    if notes:
        error.notes = notes

    await db.commit()

    return {
        "status": "success",
        "message": "Error marked as resolved",
    }


@router.get("/monitoring/alert-rules")
async def list_alert_rules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取告警规则列表"""
    stmt = select(AlertRule).order_by(AlertRule.name)
    result = await db.execute(stmt)
    rules = result.scalars().all()

    return {
        "status": "success",
        "count": len(rules),
        "rules": [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "alert_type": r.alert_type,
                "metric_name": r.metric_name,
                "operator": r.operator,
                "threshold": float(r.threshold),
                "duration_seconds": r.duration_seconds,
                "enabled": r.enabled,
                "notification_channels": r.notification_channels.split(",") if r.notification_channels else [],
                "last_triggered_at": r.last_triggered_at.isoformat() if r.last_triggered_at else None,
            }
            for r in rules
        ],
    }


@router.get("/monitoring/alerts")
async def list_alerts(
    days: int = Query(7, ge=1, le=30, description="查询天数"),
    status: Optional[str] = Query(None, description="状态 (TRIGGERED/ACKNOWLEDGED/RESOLVED)"),
    severity: Optional[str] = Query(None, description="严重程度"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取告警历史"""
    start_date = date.today() - timedelta(days=days)

    conditions = [AlertHistory.triggered_at >= start_date]

    if status:
        conditions.append(AlertHistory.status == status.upper())
    if severity:
        conditions.append(AlertHistory.severity == severity.upper())

    stmt = select(AlertHistory).where(
        and_(*conditions)
    ).order_by(desc(AlertHistory.triggered_at)).limit(limit)

    result = await db.execute(stmt)
    alerts = result.scalars().all()

    return {
        "status": "success",
        "count": len(alerts),
        "alerts": [
            {
                "id": a.id,
                "alert_type": a.alert_type,
                "metric_name": a.metric_name,
                "metric_value": float(a.metric_value),
                "threshold": float(a.threshold),
                "status": a.status,
                "severity": a.severity,
                "notification_sent": a.notification_sent,
                "triggered_at": a.triggered_at.isoformat(),
                "acknowledged_at": a.acknowledged_at.isoformat() if a.acknowledged_at else None,
                "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
            }
            for a in alerts
        ],
    }


@router.post("/monitoring/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """确认告警"""
    stmt = select(AlertHistory).where(AlertHistory.id == alert_id)
    result = await db.execute(stmt)
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = "ACKNOWLEDGED"
    alert.acknowledged_at = datetime.utcnow()
    alert.acknowledged_by = current_user.id

    await db.commit()

    return {"status": "success", "message": "Alert acknowledged"}


@router.post("/monitoring/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    notes: Optional[str] = Query(None, description="解决说明"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """解决告警"""
    stmt = select(AlertHistory).where(AlertHistory.id == alert_id)
    result = await db.execute(stmt)
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = "RESOLVED"
    alert.resolved_at = datetime.utcnow()
    alert.resolved_by = current_user.id
    if notes:
        alert.notes = notes

    await db.commit()

    return {"status": "success", "message": "Alert resolved"}
