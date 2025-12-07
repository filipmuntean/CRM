from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class Platform(str, enum.Enum):
    MARKTPLAATS = "marktplaats"
    VINTED = "vinted"
    DEPOP = "depop"
    FACEBOOK_MARKETPLACE = "facebook_marketplace"


class PlatformStatus(str, enum.Enum):
    ACTIVE = "active"
    SOLD = "sold"
    PENDING = "pending"
    DELETED = "deleted"
    ERROR = "error"


class PlatformListing(Base):
    __tablename__ = "platform_listings"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    platform = Column(Enum(Platform), nullable=False)
    platform_listing_id = Column(String(255), nullable=True)  # External ID from platform
    listing_url = Column(String(500), nullable=True)
    platform_status = Column(Enum(PlatformStatus), default=PlatformStatus.ACTIVE)

    # Sync tracking
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    sync_error = Column(String(500), nullable=True)
    needs_sync = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    product = relationship("Product", back_populates="platform_listings")

    def __repr__(self):
        return f"<PlatformListing(id={self.id}, platform='{self.platform}', listing_id='{self.platform_listing_id}')>"
