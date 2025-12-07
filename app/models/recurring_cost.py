from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, Enum
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class CostFrequency(str, enum.Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class RecurringCost(Base):
    __tablename__ = "recurring_costs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    amount = Column(Float, nullable=False)
    frequency = Column(Enum(CostFrequency), default=CostFrequency.MONTHLY)
    category = Column(String(100), nullable=True)  # e.g., "subscription", "platform_fee", "shipping"
    is_active = Column(Boolean, default=True, index=True)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<RecurringCost(id={self.id}, name='{self.name}', amount={self.amount}, frequency='{self.frequency}')>"

    def calculate_monthly_cost(self) -> float:
        """Calculate the monthly equivalent cost based on frequency"""
        if self.frequency == CostFrequency.MONTHLY:
            return self.amount
        elif self.frequency == CostFrequency.QUARTERLY:
            return self.amount / 3
        elif self.frequency == CostFrequency.YEARLY:
            return self.amount / 12
        return 0.0
