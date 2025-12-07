from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.notification import NotificationType


class NotificationBase(BaseModel):
    type: NotificationType
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1)
    extra_data: Optional[Dict[str, Any]] = None


class NotificationCreate(NotificationBase):
    pass


class Notification(NotificationBase):
    id: int
    read: bool
    created_at: datetime

    class Config:
        from_attributes = True
