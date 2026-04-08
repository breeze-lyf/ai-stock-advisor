"""
多股票列表 API
支持用户创建、管理多个自定义股票列表
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.stock_list import StockList, StockListItem

router = APIRouter()


class StockListCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="列表名称")
    description: Optional[str] = Field(None, max_length=500, description="列表描述")
    is_default: bool = False
    is_public: bool = False


class StockListItemCreate(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=20, description="股票代码")
    notes: Optional[str] = Field(None, max_length=500, description="备注")


class StockListItemResponse(BaseModel):
    id: str
    ticker: str
    notes: Optional[str]
    added_at: datetime

    class Config:
        from_attributes = True


class StockListResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    is_default: bool
    is_public: bool
    created_at: datetime
    updated_at: Optional[datetime]
    items: List[StockListItemResponse]
    item_count: int

    class Config:
        from_attributes = True


@router.get("/lists", response_model=List[StockListResponse])
async def get_stock_lists(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取用户的所有股票列表"""
    stmt = select(StockList).where(StockList.user_id == current_user.id).order_by(StockList.created_at.desc())
    result = await db.execute(stmt)
    lists = result.scalars().all()

    return [
        StockListResponse(
            id=l.id,
            name=l.name,
            description=l.description,
            is_default=l.is_default,
            is_public=l.is_public,
            created_at=l.created_at,
            updated_at=l.updated_at,
            items=[
                StockListItemResponse(
                    id=item.id,
                    ticker=item.ticker,
                    notes=item.notes,
                    added_at=item.added_at,
                )
                for item in l.items
            ],
            item_count=len(l.items),
        )
        for l in lists
    ]


@router.get("/lists/{list_id}", response_model=StockListResponse)
async def get_stock_list(
    list_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取指定股票列表详情"""
    stmt = select(StockList).where(StockList.id == list_id, StockList.user_id == current_user.id)
    result = await db.execute(stmt)
    stock_list = result.scalar_one_or_none()

    if not stock_list:
        raise HTTPException(status_code=404, detail="Stock list not found")

    return StockListResponse(
        id=stock_list.id,
        name=stock_list.name,
        description=stock_list.description,
        is_default=stock_list.is_default,
        is_public=stock_list.is_public,
        created_at=stock_list.created_at,
        updated_at=stock_list.updated_at,
        items=[
            StockListItemResponse(
                id=item.id,
                ticker=item.ticker,
                notes=item.notes,
                added_at=item.added_at,
            )
            for item in stock_list.items
        ],
        item_count=len(stock_list.items),
    )


@router.post("/lists", response_model=StockListResponse, status_code=status.HTTP_201_CREATED)
async def create_stock_list(
    data: StockListCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新的股票列表"""
    # 检查名称是否已存在
    stmt = select(StockList).where(StockList.user_id == current_user.id, StockList.name == data.name)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="List name already exists")

    # 如果设置为默认列表，先将其他默认列表设为非默认
    if data.is_default:
        stmt = select(StockList).where(StockList.user_id == current_user.id, StockList.is_default == True)
        result = await db.execute(stmt)
        for existing_list in result.scalars().all():
            existing_list.is_default = False

    stock_list = StockList(
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        is_default=data.is_default,
        is_public=data.is_public,
    )
    db.add(stock_list)
    await db.commit()
    await db.refresh(stock_list)

    return StockListResponse(
        id=stock_list.id,
        name=stock_list.name,
        description=stock_list.description,
        is_default=stock_list.is_default,
        is_public=stock_list.is_public,
        created_at=stock_list.created_at,
        updated_at=stock_list.updated_at,
        items=[],
        item_count=0,
    )


@router.put("/lists/{list_id}", response_model=StockListResponse)
async def update_stock_list(
    list_id: str,
    data: StockListCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新股票列表"""
    stmt = select(StockList).where(StockList.id == list_id, StockList.user_id == current_user.id)
    result = await db.execute(stmt)
    stock_list = result.scalar_one_or_none()

    if not stock_list:
        raise HTTPException(status_code=404, detail="Stock list not found")

    # 检查新名称是否与其他列表冲突
    if data.name != stock_list.name:
        stmt = select(StockList).where(
            StockList.user_id == current_user.id,
            StockList.name == data.name,
            StockList.id != list_id
        )
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="List name already exists")

    # 如果设置为默认列表，先将其他默认列表设为非默认
    if data.is_default and not stock_list.is_default:
        stmt = select(StockList).where(StockList.user_id == current_user.id, StockList.is_default == True)
        result = await db.execute(stmt)
        for existing_list in result.scalars().all():
            existing_list.is_default = False

    stock_list.name = data.name
    stock_list.description = data.description
    stock_list.is_default = data.is_default
    stock_list.is_public = data.is_public
    stock_list.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(stock_list)

    return StockListResponse(
        id=stock_list.id,
        name=stock_list.name,
        description=stock_list.description,
        is_default=stock_list.is_default,
        is_public=stock_list.is_public,
        created_at=stock_list.created_at,
        updated_at=stock_list.updated_at,
        items=[
            StockListItemResponse(
                id=item.id,
                ticker=item.ticker,
                notes=item.notes,
                added_at=item.added_at,
            )
            for item in stock_list.items
        ],
        item_count=len(stock_list.items),
    )


@router.delete("/lists/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_stock_list(
    list_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除股票列表"""
    stmt = select(StockList).where(StockList.id == list_id, StockList.user_id == current_user.id)
    result = await db.execute(stmt)
    stock_list = result.scalar_one_or_none()

    if not stock_list:
        raise HTTPException(status_code=404, detail="Stock list not found")

    if stock_list.is_default:
        raise HTTPException(status_code=400, detail="Cannot delete default list")

    await db.delete(stock_list)
    await db.commit()

    return None


@router.post("/lists/{list_id}/items", response_model=StockListItemResponse)
async def add_stock_to_list(
    list_id: str,
    data: StockListItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """添加股票到列表"""
    # 验证列表存在且属于当前用户
    stmt = select(StockList).where(StockList.id == list_id, StockList.user_id == current_user.id)
    result = await db.execute(stmt)
    stock_list = result.scalar_one_or_none()

    if not stock_list:
        raise HTTPException(status_code=404, detail="Stock list not found")

    # 检查股票是否已存在
    stmt = select(StockListItem).where(
        StockListItem.list_id == list_id,
        StockListItem.ticker == data.ticker
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Stock already in list")

    item = StockListItem(
        list_id=list_id,
        ticker=data.ticker,
        notes=data.notes,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    return StockListItemResponse(
        id=item.id,
        ticker=item.ticker,
        notes=item.notes,
        added_at=item.added_at,
    )


@router.delete("/lists/{list_id}/items/{ticker}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_stock_from_list(
    list_id: str,
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """从列表中移除股票"""
    stmt = select(StockListItem).where(
        StockListItem.list_id == list_id,
        StockListItem.ticker == ticker
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Stock not found in list")

    # 验证列表属于当前用户
    stmt = select(StockList).where(StockList.id == list_id, StockList.user_id == current_user.id)
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Access denied")

    await db.delete(item)
    await db.commit()

    return None
