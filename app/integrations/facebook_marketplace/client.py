from playwright.async_api import async_playwright, Page, Browser
from typing import List, Dict, Optional, Any
from datetime import datetime
import asyncio
from app.integrations.base import BasePlatformIntegration
from app.core.config import settings


class FacebookMarketplaceIntegration(BasePlatformIntegration):
    """Facebook Marketplace integration using browser automation"""

    def __init__(self):
        super().__init__()
        self.email = settings.FACEBOOK_EMAIL if hasattr(settings, "FACEBOOK_EMAIL") else None
        self.password = settings.FACEBOOK_PASSWORD if hasattr(settings, "FACEBOOK_PASSWORD") else None
        self.base_url = "https://www.facebook.com/marketplace"
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.is_authenticated = False

    async def _init_browser(self):
        """Initialize browser instance"""
        if not self.browser:
            playwright = await async_playwright().start()
            # Use persistent context to maintain cookies/session
            self.browser = await playwright.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            self.page = await self.browser.new_page()
            # Set a realistic user agent
            await self.page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            })

    async def authenticate(self) -> bool:
        """Authenticate with Facebook"""
        try:
            await self._init_browser()

            # Navigate to Facebook login
            await self.page.goto("https://www.facebook.com/login")
            await asyncio.sleep(2)

            # Fill credentials
            await self.page.fill('input[name="email"]', self.email)
            await self.page.fill('input[name="pass"]', self.password)

            # Submit login
            await self.page.click('button[name="login"]')
            await asyncio.sleep(5)

            # Check if logged in (no login page in URL)
            current_url = self.page.url
            self.is_authenticated = "/login" not in current_url

            return self.is_authenticated
        except Exception as e:
            print(f"Error authenticating with Facebook: {e}")
            return False

    async def get_listings(self) -> List[Dict[str, Any]]:
        """Get all active marketplace listings"""
        if not self.is_authenticated:
            await self.authenticate()

        try:
            # Navigate to "Your Listings" page
            await self.page.goto(f"{self.base_url}/you/selling")
            await asyncio.sleep(3)

            # Scroll to load all listings
            for _ in range(3):
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1)

            # Extract listings
            listings = await self.page.evaluate("""
                () => {
                    const items = [];
                    document.querySelectorAll('[role="article"]').forEach(listing => {
                        const titleEl = listing.querySelector('span[dir="auto"]');
                        const priceEl = listing.querySelector('span[dir="auto"]');
                        const imgEl = listing.querySelector('img');
                        const linkEl = listing.querySelector('a[href*="/marketplace/item/"]');

                        if (titleEl && priceEl && linkEl) {
                            const href = linkEl.getAttribute('href');
                            const itemId = href.match(/\\/marketplace\\/item\\/(\\d+)/)?.[1];

                            items.push({
                                id: itemId,
                                title: titleEl.textContent.trim(),
                                price: parseFloat(priceEl.textContent.replace(/[^0-9.]/g, '')),
                                image: imgEl ? imgEl.src : null,
                                url: 'https://www.facebook.com' + href
                            });
                        }
                    });
                    return items;
                }
            """)

            return listings
        except Exception as e:
            print(f"Error fetching Facebook Marketplace listings: {e}")
            return []

    async def create_listing(self, product_data: Dict[str, Any]) -> Optional[str]:
        """Create a new listing on Facebook Marketplace"""
        if not self.is_authenticated:
            await self.authenticate()

        try:
            # Navigate to create listing page
            await self.page.goto(f"{self.base_url}/create/item")
            await asyncio.sleep(3)

            # Fill in title
            await self.page.fill('input[placeholder*="Title"]', product_data["title"])
            await asyncio.sleep(1)

            # Fill in price
            await self.page.fill('input[placeholder*="Price"]', str(product_data["price"]))
            await asyncio.sleep(1)

            # Select category
            if product_data.get("category"):
                await self.page.click('div[role="button"]:has-text("Category")')
                await asyncio.sleep(1)
                await self.page.click(f'span:has-text("{product_data["category"]}")')
                await asyncio.sleep(1)

            # Condition
            if product_data.get("condition"):
                await self.page.click('div[role="button"]:has-text("Condition")')
                await asyncio.sleep(1)
                await self.page.click(f'span:has-text("{product_data["condition"]}")')
                await asyncio.sleep(1)

            # Description
            if product_data.get("description"):
                await self.page.fill('textarea[placeholder*="Description"]', product_data["description"])
                await asyncio.sleep(1)

            # Submit listing
            await self.page.click('div[role="button"]:has-text("Next")')
            await asyncio.sleep(2)
            await self.page.click('div[role="button"]:has-text("Publish")')
            await asyncio.sleep(3)

            # Try to extract listing ID from success page or redirect
            current_url = self.page.url
            listing_id = None
            if "/marketplace/item/" in current_url:
                listing_id = current_url.split("/marketplace/item/")[1].split("/")[0]

            return listing_id
        except Exception as e:
            print(f"Error creating Facebook Marketplace listing: {e}")
            return None

    async def update_listing(self, listing_id: str, product_data: Dict[str, Any]) -> bool:
        """Update an existing listing"""
        if not self.is_authenticated:
            await self.authenticate()

        try:
            # Navigate to listing
            await self.page.goto(f"{self.base_url}/item/{listing_id}")
            await asyncio.sleep(2)

            # Click edit button (usually in menu)
            await self.page.click('div[aria-label="More"]')
            await asyncio.sleep(1)
            await self.page.click('span:has-text("Edit listing")')
            await asyncio.sleep(2)

            # Update fields
            await self.page.fill('input[placeholder*="Title"]', product_data["title"])
            await self.page.fill('input[placeholder*="Price"]', str(product_data["price"]))

            if product_data.get("description"):
                await self.page.fill('textarea[placeholder*="Description"]', product_data["description"])

            # Save changes
            await self.page.click('div[role="button"]:has-text("Save")')
            await asyncio.sleep(2)

            return True
        except Exception as e:
            print(f"Error updating Facebook Marketplace listing: {e}")
            return False

    async def delete_listing(self, listing_id: str) -> bool:
        """Delete a listing"""
        if not self.is_authenticated:
            await self.authenticate()

        try:
            # Navigate to listing
            await self.page.goto(f"{self.base_url}/item/{listing_id}")
            await asyncio.sleep(2)

            # Click options menu
            await self.page.click('div[aria-label="More"]')
            await asyncio.sleep(1)

            # Click delete
            await self.page.click('span:has-text("Delete listing")')
            await asyncio.sleep(1)

            # Confirm deletion
            await self.page.click('div[role="button"]:has-text("Delete")')
            await asyncio.sleep(2)

            return True
        except Exception as e:
            print(f"Error deleting Facebook Marketplace listing: {e}")
            return False

    async def mark_as_sold(self, listing_id: str) -> bool:
        """Mark listing as sold"""
        if not self.is_authenticated:
            await self.authenticate()

        try:
            # Navigate to listing
            await self.page.goto(f"{self.base_url}/item/{listing_id}")
            await asyncio.sleep(2)

            # Click options menu
            await self.page.click('div[aria-label="More"]')
            await asyncio.sleep(1)

            # Mark as sold
            await self.page.click('span:has-text("Mark as sold")')
            await asyncio.sleep(2)

            return True
        except Exception as e:
            print(f"Error marking Facebook Marketplace listing as sold: {e}")
            return False

    async def get_sales(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get sales information - Facebook doesn't have a dedicated sales API"""
        # Facebook Marketplace doesn't provide direct sales history
        # Users typically communicate through Messenger to complete sales
        return []

    async def check_listing_status(self, listing_id: str) -> Optional[str]:
        """Check listing status"""
        if not self.is_authenticated:
            await self.authenticate()

        try:
            response = await self.page.goto(f"{self.base_url}/item/{listing_id}")

            if response.status == 404:
                return "deleted"

            # Check for sold indicator
            is_sold = await self.page.locator('text=Marked as sold').count() > 0

            return "sold" if is_sold else "active"
        except Exception as e:
            print(f"Error checking Facebook Marketplace listing status: {e}")
            return None

    async def close(self):
        """Close browser instance"""
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.page = None
