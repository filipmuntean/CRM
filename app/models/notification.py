from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Enum, JSON
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class NotificationType(str, enum.Enum):
    SALE = "sale"
    SYNC_ERROR = "sync_error"
    PRICE_SUGGESTION = "price_suggestion"
    INVENTORY_ALERT = "inventory_alert"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(Enum(NotificationType), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    read = Column(Boolean, default=False, index=True)
    extra_data = Column("metadata", JSON, nullable=True)  # Additional data (product_id, sale_id, etc.)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def __repr__(self):
        return f"<Notification(id={self.id}, type='{self.type}', title='{self.title}', read={self.read})>"
