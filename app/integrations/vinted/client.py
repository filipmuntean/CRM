from playwright.async_api import async_playwright, Page, Browser
from typing import List, Dict, Optional, Any
from datetime import datetime
import asyncio
from app.integrations.base import BasePlatformIntegration
from app.core.config import settings


class VintedIntegration(BasePlatformIntegration):
    """Vinted integration using browser automation (Playwright)"""

    def __init__(self):
        super().__init__()
        self.email = settings.VINTED_EMAIL
        self.password = settings.VINTED_PASSWORD
        self.base_url = settings.VINTED_BASE_URL
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
        """Authenticate with Vinted using browser automation"""
        try:
            await self._init_browser()

            # Navigate to login page
            await self.page.goto(f"{self.base_url}/auth/login")
            await asyncio.sleep(2)

            # Fill in credentials
            await self.page.fill('input[name="username"]', self.email)
            await self.page.fill('input[name="password"]', self.password)

            # Submit login form
            await self.page.click('button[type="submit"]')
            await asyncio.sleep(3)

            # Check if login was successful
            current_url = self.page.url
            self.is_authenticated = "/auth/login" not in current_url

            return self.is_authenticated
        except Exception as e:
            print(f"Error authenticating with Vinted: {e}")
            return False

    async def get_listings(self) -> List[Dict[str, Any]]:
        """Get all active listings from Vinted"""
        if not self.is_authenticated:
            await self.authenticate()

        try:
            # Navigate to user's items page
            await self.page.goto(f"{self.base_url}/member/general/my-items")
            await asyncio.sleep(2)

            # Extract listings using JavaScript
            listings = await self.page.evaluate("""
                () => {
                    const items = [];
                    document.querySelectorAll('.item-box').forEach(item => {
                        const titleEl = item.querySelector('.item-box__title');
                        const priceEl = item.querySelector('.item-box__price');
                        const imgEl = item.querySelector('img');
                        const linkEl = item.querySelector('a');

                        if (titleEl && priceEl) {
                            items.push({
                                id: linkEl ? linkEl.href.split('/').pop() : null,
                                title: titleEl.textContent.trim(),
                                price: parseFloat(priceEl.textContent.replace(/[^0-9.,]/g, '').replace(',', '.')),
                                image: imgEl ? imgEl.src : null,
                                url: linkEl ? linkEl.href : null
                            });
                        }
                    });
                    return items;
                }
            """)

            return listings
        except Exception as e:
            print(f"Error fetching Vinted listings: {e}")
            return []

    async def create_listing(self, product_data: Dict[str, Any]) -> Optional[str]:
        """Create a new listing on Vinted"""
        if not self.is_authenticated:
            await self.authenticate()

        try:
            # Navigate to upload page
            await self.page.goto(f"{self.base_url}/items/new")
            await asyncio.sleep(2)

            # Fill in product details
            await self.page.fill('input[name="title"]', product_data["title"])
            await self.page.fill('textarea[name="description"]', product_data.get("description", ""))
            await self.page.fill('input[name="price"]', str(product_data["price"]))

            # Select category if available
            if product_data.get("category"):
                await self.page.click('select[name="catalog_id"]')
                await self.page.select_option('select[name="catalog_id"]', label=product_data["category"])

            # Fill size if available
            if product_data.get("size"):
                await self.page.fill('input[name="size_title"]', product_data["size"])

            # Fill brand if available
            if product_data.get("brand"):
                await self.page.fill('input[name="brand_title"]', product_data["brand"])

            # Submit the form
            await self.page.click('button[type="submit"]')
            await asyncio.sleep(3)

            # Get the new listing ID from URL
            new_url = self.page.url
            listing_id = new_url.split("/")[-1] if "/items/" in new_url else None

            return listing_id
        except Exception as e:
            print(f"Error creating Vinted listing: {e}")
            return None

    async def update_listing(self, listing_id: str, product_data: Dict[str, Any]) -> bool:
        """Update an existing listing"""
        if not self.is_authenticated:
            await self.authenticate()

        try:
            # Navigate to edit page
            await self.page.goto(f"{self.base_url}/items/{listing_id}/edit")
            await asyncio.sleep(2)

            # Update fields
            await self.page.fill('input[name="title"]', product_data["title"])
            await self.page.fill('textarea[name="description"]', product_data.get("description", ""))
            await self.page.fill('input[name="price"]', str(product_data["price"]))

            # Submit changes
            await self.page.click('button[type="submit"]')
            await asyncio.sleep(2)

            return True
        except Exception as e:
            print(f"Error updating Vinted listing: {e}")
            return False

    async def delete_listing(self, listing_id: str) -> bool:
        """Delete a listing"""
        if not self.is_authenticated:
            await self.authenticate()

        try:
            # Navigate to item page
            await self.page.goto(f"{self.base_url}/items/{listing_id}")
            await asyncio.sleep(2)

            # Click delete button
            await self.page.click('button[data-action="delete"]')
            await asyncio.sleep(1)

            # Confirm deletion
            await self.page.click('button[data-testid="confirm-delete"]')
            await asyncio.sleep(2)

            return True
        except Exception as e:
            print(f"Error deleting Vinted listing: {e}")
            return False

    async def mark_as_sold(self, listing_id: str) -> bool:
        """Mark listing as sold"""
        # Vinted typically marks items as sold automatically when purchased
        # But we can deactivate the listing
        return await self.delete_listing(listing_id)

    async def get_sales(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get sales information"""
        if not self.is_authenticated:
            await self.authenticate()

        try:
            # Navigate to sales page
            await self.page.goto(f"{self.base_url}/member/orders/sold")
            await asyncio.sleep(2)

            # Extract sales data
            sales = await self.page.evaluate("""
                () => {
                    const items = [];
                    document.querySelectorAll('.order-item').forEach(order => {
                        const titleEl = order.querySelector('.order-item__title');
                        const priceEl = order.querySelector('.order-item__price');
                        const dateEl = order.querySelector('.order-item__date');

                        if (titleEl && priceEl) {
                            items.push({
                                title: titleEl.textContent.trim(),
                                price: parseFloat(priceEl.textContent.replace(/[^0-9.,]/g, '').replace(',', '.')),
                                date: dateEl ? dateEl.textContent.trim() : null
                            });
                        }
                    });
                    return items;
                }
            """)

            return sales
        except Exception as e:
            print(f"Error fetching Vinted sales: {e}")
            return []

    async def check_listing_status(self, listing_id: str) -> Optional[str]:
        """Check if listing is active"""
        if not self.is_authenticated:
            await self.authenticate()

        try:
            response = await self.page.goto(f"{self.base_url}/items/{listing_id}")

            if response.status == 404:
                return "deleted"

            # Check if item shows as sold
            is_sold = await self.page.locator('text=Sold').count() > 0

            return "sold" if is_sold else "active"
        except Exception as e:
            print(f"Error checking Vinted listing status: {e}")
            return None

    async def close(self):
        """Close browser instance"""
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.page = None
