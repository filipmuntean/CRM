from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from app.core.database import get_db
from app.models.sale import Sale
from app.models.platform_listing import Platform
from pydantic import BaseModel

router = APIRouter(prefix="/sales", tags=["sales"])


class SaleResponse(BaseModel):
    id: int
    product_id: int
    platform: str
    sale_price: float
    sale_date: datetime
    net_profit: Optional[float]
    synced_to_sheets: bool

    class Config:
        from_attributes = True


@router.get("/", response_model=List[SaleResponse])
def get_sales(
    skip: int = 0,
    limit: int = 100,
    platform: Optional[Platform] = None,
    days: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get all sales with optional filters"""
    query = db.query(Sale)

    if platform:
        query = query.filter(Sale.platform == platform)

    if days:
        since_date = datetime.now() - timedelta(days=days)
        query = query.filter(Sale.sale_date >= since_date)

    sales = query.order_by(Sale.sale_date.desc()).offset(skip).limit(limit).all()
    return sales


@router.get("/stats")
def get_sales_stats(
    days: Optional[int] = 30,
    db: Session = Depends(get_db)
):
    """Get sales statistics"""
    from sqlalchemy import func

    # Base query
    query = db.query(Sale)

    if days:
        since_date = datetime.now() - timedelta(days=days)
        query = query.filter(Sale.sale_date >= since_date)

    # Total stats
    total_sales = query.count()
    total_revenue = db.query(func.sum(Sale.sale_price)).filter(
        Sale.sale_date >= (datetime.now() - timedelta(days=days)) if days else True
    ).scalar() or 0

    total_profit = db.query(func.sum(Sale.net_profit)).filter(
        Sale.sale_date >= (datetime.now() - timedelta(days=days)) if days else True
    ).scalar() or 0

    # Platform breakdown
    platform_sales = db.query(
        Sale.platform,
        func.count(Sale.id),
        func.sum(Sale.sale_price),
        func.sum(Sale.net_profit)
    ).filter(
        Sale.sale_date >= (datetime.now() - timedelta(days=days)) if days else True
    ).group_by(Sale.platform).all()

    platform_breakdown = {
        platform.value: {
            "count": count,
            "revenue": float(revenue or 0),
            "profit": float(profit or 0)
        }
        for platform, count, revenue, profit in platform_sales
    }

    return {
        "period_days": days,
        "total_sales": total_sales,
        "total_revenue": float(total_revenue),
        "total_profit": float(total_profit),
        "average_sale_price": float(total_revenue / total_sales) if total_sales > 0 else 0,
        "by_platform": platform_breakdown
    }


@router.get("/{sale_id}", response_model=SaleResponse)
def get_sale(sale_id: int, db: Session = Depends(get_db)):
    """Get a specific sale"""
    sale = db.query(Sale).filter(Sale.id == sale_id).first()

    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    return sale
