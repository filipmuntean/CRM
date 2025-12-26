from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.product import ProductStatus


class ProductBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    images: List[str] = Field(default_factory=list)
    category: Optional[str] = None
    size: Optional[str] = None
    condition: Optional[str] = None
    brand: Optional[str] = None
    color: Optional[str] = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    images: Optional[List[str]] = None
    category: Optional[str] = None
    size: Optional[str] = None
    condition: Optional[str] = None
    brand: Optional[str] = None
    color: Optional[str] = None
    status: Optional[ProductStatus] = None


class Product(ProductBase):
    id: int
    status: ProductStatus
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PlatformListingInfo(BaseModel):
    id: int
    platform: str
    platform_listing_id: Optional[str]
    listing_url: Optional[str]
    platform_status: str
    last_synced_at: Optional[datetime]

    class Config:
        from_attributes = True


class ProductWithListings(Product):
    platform_listings: List[PlatformListingInfo] = []

    class Config:
        from_attributes = True
