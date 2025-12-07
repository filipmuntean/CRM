from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.recurring_cost import CostFrequency


class RecurringCostBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    amount: float = Field(..., gt=0)
    frequency: CostFrequency = CostFrequency.MONTHLY
    category: Optional[str] = Field(None, max_length=100)
    start_date: datetime
    end_date: Optional[datetime] = None


class RecurringCostCreate(RecurringCostBase):
    pass


class RecurringCostUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    amount: Optional[float] = Field(None, gt=0)
    frequency: Optional[CostFrequency] = None
    category: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class RecurringCost(RecurringCostBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
