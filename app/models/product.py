from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class ProductStatus(str, enum.Enum):
    ACTIVE = "active"
    SOLD = "sold"
    PENDING = "pending"
    INACTIVE = "inactive"


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    images = Column(JSON, default=list)  # List of image URLs
    category = Column(String(100), nullable=True)
    size = Column(String(50), nullable=True)
    condition = Column(String(50), nullable=True)
    brand = Column(String(100), nullable=True)
    color = Column(String(50), nullable=True)
    status = Column(Enum(ProductStatus), default=ProductStatus.ACTIVE)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    platform_listings = relationship("PlatformListing", back_populates="product", cascade="all, delete-orphan")
    sales = relationship("Sale", back_populates="product", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Product(id={self.id}, title='{self.title}', status='{self.status}')>"
