from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from datetime import datetime


class BasePlatformIntegration(ABC):
    """Base class for all platform integrations"""

    def __init__(self):
        self.platform_name = self.__class__.__name__.replace("Integration", "").lower()

    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the platform"""
        pass

    @abstractmethod
    async def get_listings(self) -> List[Dict[str, Any]]:
        """Get all active listings from the platform"""
        pass

    @abstractmethod
    async def create_listing(self, product_data: Dict[str, Any]) -> Optional[str]:
        """
        Create a new listing on the platform
        Returns the platform's listing ID if successful
        """
        pass

    @abstractmethod
    async def update_listing(self, listing_id: str, product_data: Dict[str, Any]) -> bool:
        """Update an existing listing"""
        pass

    @abstractmethod
    async def delete_listing(self, listing_id: str) -> bool:
        """Delete/deactivate a listing"""
        pass

    @abstractmethod
    async def mark_as_sold(self, listing_id: str) -> bool:
        """Mark a listing as sold"""
        pass

    @abstractmethod
    async def get_sales(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get sales information from the platform"""
        pass

    @abstractmethod
    async def check_listing_status(self, listing_id: str) -> Optional[str]:
        """Check if a listing is still active, sold, or deleted"""
        pass

    def normalize_product_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize platform-specific product data to a common format
        Override this method in subclasses if needed
        """
        return {
            "title": raw_data.get("title", ""),
            "description": raw_data.get("description", ""),
            "price": float(raw_data.get("price", 0)),
            "images": raw_data.get("images", []),
            "category": raw_data.get("category"),
            "size": raw_data.get("size"),
            "condition": raw_data.get("condition"),
            "brand": raw_data.get("brand"),
            "color": raw_data.get("color"),
        }
