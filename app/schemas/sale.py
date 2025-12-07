from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.platform_listing import Platform


class SaleBase(BaseModel):
    product_id: int
    platform: Platform
    sale_price: float = Field(..., gt=0)
    sale_date: datetime
    buyer_info: Optional[Dict[str, Any]] = None
    shipping_cost: float = Field(default=0.0, ge=0)
    platform_fee: float = Field(default=0.0, ge=0)
    payment_fee: float = Field(default=0.0, ge=0)
    vat_amount: float = Field(default=0.0, ge=0)
    original_cost: float = Field(default=0.0, ge=0)
    notes: Optional[str] = None


class SaleCreate(SaleBase):
    pass


class SaleUpdate(BaseModel):
    sale_price: Optional[float] = Field(None, gt=0)
    sale_date: Optional[datetime] = None
    buyer_info: Optional[Dict[str, Any]] = None
    shipping_cost: Optional[float] = Field(None, ge=0)
    platform_fee: Optional[float] = Field(None, ge=0)
    payment_fee: Optional[float] = Field(None, ge=0)
    vat_amount: Optional[float] = Field(None, ge=0)
    original_cost: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None


class Sale(SaleBase):
    id: int
    net_profit: Optional[float] = None
    synced_to_sheets: bool
    sheets_row_number: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
