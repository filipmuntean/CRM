from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class ProductMetrics(Base):
    __tablename__ = "product_metrics"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, unique=True, index=True)
    days_listed = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    times_price_reduced = Column(Integer, default=0)
    original_listing_price = Column(Float, nullable=True)
    optimal_price_suggestion = Column(Float, nullable=True)
    last_price_check = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    product = relationship("Product", back_populates="metrics")

    def __repr__(self):
        return f"<ProductMetrics(id={self.id}, product_id={self.product_id}, days_listed={self.days_listed})>"
