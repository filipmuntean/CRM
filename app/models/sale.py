from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.platform_listing import Platform


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    platform = Column(Enum(Platform), nullable=False)

    # Sale details
    sale_price = Column(Float, nullable=False)
    sale_date = Column(DateTime(timezone=True), nullable=False)
    buyer_info = Column(JSON, nullable=True)  # Store buyer details if available

    # Tracking & fees
    shipping_cost = Column(Float, default=0.0)
    platform_fee = Column(Float, default=0.0)
    payment_fee = Column(Float, default=0.0)
    net_profit = Column(Float, nullable=True)  # sale_price - fees - original_cost

    # Google Sheets sync
    synced_to_sheets = Column(Boolean, default=False)
    sheets_row_number = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    product = relationship("Product", back_populates="sales")

    def calculate_net_profit(self, original_cost: float = 0.0):
        """Calculate net profit after all fees"""
        self.net_profit = self.sale_price - self.shipping_cost - self.platform_fee - self.payment_fee - original_cost
        return self.net_profit

    def __repr__(self):
        return f"<Sale(id={self.id}, product_id={self.product_id}, platform='{self.platform}', price={self.sale_price})>"
