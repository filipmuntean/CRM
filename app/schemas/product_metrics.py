from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ProductMetricsBase(BaseModel):
    days_listed: int = 0
    view_count: int = 0
    times_price_reduced: int = 0
    original_listing_price: Optional[float] = None
    optimal_price_suggestion: Optional[float] = None


class ProductMetricsCreate(ProductMetricsBase):
    product_id: int


class ProductMetricsUpdate(BaseModel):
    days_listed: Optional[int] = None
    view_count: Optional[int] = None
    times_price_reduced: Optional[int] = None
    optimal_price_suggestion: Optional[float] = None


class ProductMetrics(ProductMetricsBase):
    id: int
    product_id: int
    last_price_check: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
