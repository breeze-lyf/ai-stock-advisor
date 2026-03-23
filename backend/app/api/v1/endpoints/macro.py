import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from app.models.user import User
from app.api import deps
from app.services.macro_service import MacroService
from app.core import security
from app.utils.time import utc_now_naive

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/radar")
async def get_macro_radar(
    background_tasks: BackgroundTasks,
    refresh: bool = Query(False),
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user)
):
    """获取宏观雷达热点，支持静默自动刷新"""
    topics = await MacroService.get_latest_radar(db)
    
    # 逻辑：如果强制刷新，或者数据库为空，或者最新数据早于 4 小时前，则触发更新
    should_auto_update = False
    if not topics:
        should_auto_update = True
    else:
        last_updated = topics[0].updated_at
        if utc_now_naive() - last_updated > timedelta(hours=5):
            should_auto_update = True
            
    if refresh or should_auto_update:
        # 使用 BackgroundTasks 进行异步更新，不阻塞当前请求
        # 注意：此处不再传递 db，由 MacroService 内部按需创建 Session，避免会话冲突
        background_tasks.add_task(MacroService.update_global_radar)
        
    return topics

@router.get("/cls_news")
async def get_cls_news(
    background_tasks: BackgroundTasks,
    refresh: bool = Query(False),
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user)
):
    """
    获取数据库中持久化的最新全球快讯。
    逻辑：DB 优先，根据新鲜度自动触发后台更新。支持 refresh=True 强制刷新。
    """
    # 如果强制刷新，先执行同步逻辑 (akshare 抓取大约 0.3s，可以同步执行以给用户即时反馈)
    if refresh:
        await MacroService.update_cls_news(db)
        
    news_items = await MacroService.get_latest_news(db, limit=50)
    
    # 判定新鲜度 (10 分钟) 用于自动触发
    should_update = False
    if not refresh:
        if not news_items:
            should_update = True
        else:
            # 以第一条（最新的）的时间为准
            if utc_now_naive() - news_items[0].created_at > timedelta(minutes=10):
                should_update = True
            
    if should_update:
        background_tasks.add_task(MacroService.update_cls_news)
        
    # 格式化为前端所需字段
    return [
        {
            "time": item.published_at,
            "title": item.title,
            "content": item.content
        } for item in news_items
    ]
