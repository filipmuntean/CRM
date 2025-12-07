from playwright.async_api import async_playwright, Page, Browser
from typing import List, Dict, Optional, Any
from datetime import datetime
import asyncio
from app.integrations.base import BasePlatformIntegration
from app.core.config import settings


class DepopIntegration(BasePlatformIntegration):
    """Depop integration using browser automation"""

    def __init__(self):
        super().__init__()
        self.username = settings.DEPOP_USERNAME
        self.password = settings.DEPOP_PASSWORD
        self.base_url = settings.DEPOP_BASE_URL
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.is_authenticated = False

    async def _init_browser(self):
        """Initialize browser instance"""
        if not self.browser:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=True)
            self.page = await self.browser.new_page()

    async def authenticate(self) -> bool:
        """Authenticate with Depop"""
        try:
            await self._init_browser()

            # Navigate to login page
            await self.page.goto(f"{self.base_url}/login")
            await asyncio.sleep(2)

            # Fill in credentials
            await self.page.fill('input[name="username"]', self.username)
            await self.page.fill('input[name="password"]', self.password)

            # Submit login
            await self.page.click('button[type="submit"]')
            await asyncio.sleep(3)

            # Check if logged in
            current_url = self.page.url
            self.is_authenticated = "/login" not in current_url

            return self.is_authenticated
        except Exception as e:
            print(f"Error authenticating with Depop: {e}")
            return False

    async def get_listings(self) -> List[Dict[str, Any]]:
        """Get all active listings"""
        if not self.is_authenticated:
            await self.authenticate()

        try:
            # Navigate to user's shop
            await self.page.goto(f"{self.base_url}/{self.username}")
            await asyncio.sleep(2)

            # Scroll to load all items
            for _ in range(5):
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1)

            # Extract product data
            listings = await self.page.evaluate("""
                () => {
                    const items = [];
                    document.querySelectorAll('[data-testid="product"]').forEach(product => {
                        const link = product.querySelector('a');
                        const img = product.querySelector('img');
                        const price = product.querySelector('[data-testid="product__price"]');
                        const title = product.querySelector('[data-testid="product__title"]');

                        if (link && price && title) {
                            items.push({
                                id: link.href.split('/products/')[1],
                                title: title.textContent.trim(),
                                price: parseFloat(price.textContent.replace(/[^0-9.]/g, '')),
                                image: img ? img.src : null,
                                url: link.href
                            });
                        }
                    });
                    return items;
                }
            """)

            return listings
        except Exception as e:
            print(f"Error fetching Depop listings: {e}")
            return []

    async def create_listing(self, product_data: Dict[str, Any]) -> Optional[str]:
        """Create a new listing on Depop"""
        if not self.is_authenticated:
            await self.authenticate()

        try:
            # Navigate to sell page
            await self.page.goto(f"{self.base_url}/sell")
            await asyncio.sleep(2)

            # Fill product details
            await self.page.fill('input[name="title"]', product_data["title"])
            await self.page.fill('textarea[name="description"]', product_data.get("description", ""))
            await self.page.fill('input[name="price"]', str(product_data["price"]))

            # Category selection
            if product_data.get("category"):
                await self.page.click('select[name="category"]')
                await self.page.select_option('select[name="category"]', label=product_data["category"])

            # Size
            if product_data.get("size"):
                await self.page.fill('input[name="size"]', product_data["size"])

            # Brand
            if product_data.get("brand"):
                await self.page.fill('input[name="brand"]', product_data["brand"])

            # Condition
            if product_data.get("condition"):
                await self.page.click(f'button[data-condition="{product_data["condition"].lower()}"]')

            # Submit listing
            await self.page.click('button[type="submit"]')
            await asyncio.sleep(3)

            # Extract listing ID from URL
            new_url = self.page.url
            listing_id = new_url.split("/products/")[-1] if "/products/" in new_url else None

            return listing_id
        except Exception as e:
            print(f"Error creating Depop listing: {e}")
            return None

    async def update_listing(self, listing_id: str, product_data: Dict[str, Any]) -> bool:
        """Update an existing listing"""
        if not self.is_authenticated:
            await self.authenticate()

        try:
            # Navigate to edit page
            await self.page.goto(f"{self.base_url}/products/{listing_id}/edit")
            await asyncio.sleep(2)

            # Update fields
            await self.page.fill('input[name="title"]', product_data["title"])
            await self.page.fill('textarea[name="description"]', product_data.get("description", ""))
            await self.page.fill('input[name="price"]', str(product_data["price"]))

            # Save changes
            await self.page.click('button[type="submit"]')
            await asyncio.sleep(2)

            return True
        except Exception as e:
            print(f"Error updating Depop listing: {e}")
            return False

    async def delete_listing(self, listing_id: str) -> bool:
        """Delete a listing"""
        if not self.is_authenticated:
            await self.authenticate()

        try:
            # Navigate to product page
            await self.page.goto(f"{self.base_url}/products/{listing_id}")
            await asyncio.sleep(2)

            # Click options menu
            await self.page.click('[data-testid="product-options"]')
            await asyncio.sleep(1)

            # Click delete
            await self.page.click('button:has-text("Delete")')
            await asyncio.sleep(1)

            # Confirm deletion
            await self.page.click('button[data-testid="confirm-delete"]')
            await asyncio.sleep(2)

            return True
        except Exception as e:
            print(f"Error deleting Depop listing: {e}")
            return False

    async def mark_as_sold(self, listing_id: str) -> bool:
        """Mark listing as sold"""
        if not self.is_authenticated:
            await self.authenticate()

        try:
            # Navigate to product page
            await self.page.goto(f"{self.base_url}/products/{listing_id}")
            await asyncio.sleep(2)

            # Click options menu
            await self.page.click('[data-testid="product-options"]')
            await asyncio.sleep(1)

            # Mark as sold
            await self.page.click('button:has-text("Mark as sold")')
            await asyncio.sleep(2)

            return True
        except Exception as e:
            print(f"Error marking Depop listing as sold: {e}")
            return False

    async def get_sales(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get sales information"""
        if not self.is_authenticated:
            await self.authenticate()

        try:
            # Navigate to receipts/sales page
            await self.page.goto(f"{self.base_url}/receipts/selling")
            await asyncio.sleep(2)

            # Extract sales data
            sales = await self.page.evaluate("""
                () => {
                    const items = [];
                    document.querySelectorAll('[data-testid="receipt"]').forEach(receipt => {
                        const title = receipt.querySelector('[data-testid="receipt__title"]');
                        const price = receipt.querySelector('[data-testid="receipt__price"]');
                        const date = receipt.querySelector('[data-testid="receipt__date"]');

                        if (title && price) {
                            items.push({
                                title: title.textContent.trim(),
                                price: parseFloat(price.textContent.replace(/[^0-9.]/g, '')),
                                date: date ? date.textContent.trim() : null
                            });
                        }
                    });
                    return items;
                }
            """)

            return sales
        except Exception as e:
            print(f"Error fetching Depop sales: {e}")
            return []

    async def check_listing_status(self, listing_id: str) -> Optional[str]:
        """Check listing status"""
        if not self.is_authenticated:
            await self.authenticate()

        try:
            response = await self.page.goto(f"{self.base_url}/products/{listing_id}")

            if response.status == 404:
                return "deleted"

            # Check if marked as sold
            is_sold = await self.page.locator('text=Sold').count() > 0

            return "sold" if is_sold else "active"
        except Exception as e:
            print(f"Error checking Depop listing status: {e}")
            return None

    async def close(self):
        """Close browser instance"""
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.page = None
