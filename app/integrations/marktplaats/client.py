import httpx
from typing import List, Dict, Optional, Any
from datetime import datetime
from app.integrations.base import BasePlatformIntegration
from app.core.config import settings


class MarktplaatsIntegration(BasePlatformIntegration):
    """Marktplaats official API integration"""

    def __init__(self):
        super().__init__()
        self.client_id = settings.MARKTPLAATS_CLIENT_ID
        self.client_secret = settings.MARKTPLAATS_CLIENT_SECRET
        self.redirect_uri = settings.MARKTPLAATS_REDIRECT_URI
        self.base_url = settings.MARKTPLAATS_API_BASE_URL
        self.access_token = None
        self.refresh_token = None

    async def authenticate(self) -> bool:
        """Authenticate using OAuth2"""
        # This will be called after the OAuth2 callback
        # Token exchange happens in the API endpoint
        return self.access_token is not None

    def set_tokens(self, access_token: str, refresh_token: str = None):
        """Set OAuth tokens (called after OAuth2 flow)"""
        self.access_token = access_token
        self.refresh_token = refresh_token

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated request to Marktplaats API"""
        if not self.access_token:
            raise Exception("Not authenticated. Please complete OAuth2 flow first.")

        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.access_token}"

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                f"{self.base_url}{endpoint}",
                headers=headers,
                **kwargs
            )
            response.raise_for_status()
            return response.json()

    async def get_listings(self) -> List[Dict[str, Any]]:
        """Get all active listings"""
        try:
            data = await self._make_request("GET", "/advertisements")
            return data.get("advertisements", [])
        except Exception as e:
            print(f"Error fetching Marktplaats listings: {e}")
            return []

    async def create_listing(self, product_data: Dict[str, Any]) -> Optional[str]:
        """Create a new listing on Marktplaats"""
        try:
            # Transform product data to Marktplaats format
            listing_data = {
                "title": product_data["title"],
                "description": product_data["description"],
                "price": {
                    "amount": int(product_data["price"] * 100),  # Convert to cents
                    "currency": "EUR"
                },
                "categoryId": product_data.get("category", ""),
                "attributes": self._build_attributes(product_data),
                "images": product_data.get("images", [])
            }

            response = await self._make_request("POST", "/advertisements", json=listing_data)
            return response.get("id")
        except Exception as e:
            print(f"Error creating Marktplaats listing: {e}")
            return None

    async def update_listing(self, listing_id: str, product_data: Dict[str, Any]) -> bool:
        """Update an existing listing"""
        try:
            listing_data = {
                "title": product_data["title"],
                "description": product_data["description"],
                "price": {
                    "amount": int(product_data["price"] * 100),
                    "currency": "EUR"
                }
            }

            await self._make_request("PUT", f"/advertisements/{listing_id}", json=listing_data)
            return True
        except Exception as e:
            print(f"Error updating Marktplaats listing: {e}")
            return False

    async def delete_listing(self, listing_id: str) -> bool:
        """Delete a listing"""
        try:
            await self._make_request("DELETE", f"/advertisements/{listing_id}")
            return True
        except Exception as e:
            print(f"Error deleting Marktplaats listing: {e}")
            return False

    async def mark_as_sold(self, listing_id: str) -> bool:
        """Mark listing as sold"""
        try:
            await self._make_request("POST", f"/advertisements/{listing_id}/sold")
            return True
        except Exception as e:
            print(f"Error marking Marktplaats listing as sold: {e}")
            return False

    async def get_sales(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get sales information"""
        try:
            params = {}
            if since:
                params["since"] = since.isoformat()

            data = await self._make_request("GET", "/sales", params=params)
            return data.get("sales", [])
        except Exception as e:
            print(f"Error fetching Marktplaats sales: {e}")
            return []

    async def check_listing_status(self, listing_id: str) -> Optional[str]:
        """Check listing status"""
        try:
            data = await self._make_request("GET", f"/advertisements/{listing_id}")
            return data.get("status")
        except Exception as e:
            print(f"Error checking Marktplaats listing status: {e}")
            return None

    def _build_attributes(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build platform-specific attributes"""
        attributes = {}
        if product_data.get("size"):
            attributes["size"] = product_data["size"]
        if product_data.get("condition"):
            attributes["condition"] = product_data["condition"]
        if product_data.get("brand"):
            attributes["brand"] = product_data["brand"]
        if product_data.get("color"):
            attributes["color"] = product_data["color"]
        return attributes

    def get_oauth_url(self) -> str:
        """Get OAuth2 authorization URL"""
        return (
            f"{self.base_url}/oauth/authorize?"
            f"client_id={self.client_id}&"
            f"redirect_uri={self.redirect_uri}&"
            f"response_type=code&"
            f"scope=listings:read listings:write sales:read"
        )
