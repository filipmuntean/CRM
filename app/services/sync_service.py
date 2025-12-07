from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio

from app.models.product import Product, ProductStatus
from app.models.platform_listing import PlatformListing, Platform, PlatformStatus
from app.models.sale import Sale
from app.integrations.marktplaats.client import MarktplaatsIntegration
from app.integrations.vinted.client import VintedIntegration
from app.integrations.depop.client import DepopIntegration
from app.integrations.facebook_marketplace.client import FacebookMarketplaceIntegration
from app.services.sheets_service import GoogleSheetsService


class SyncService:
    """
    Core synchronization service that manages product listings across all platforms
    """

    def __init__(self, db: Session):
        self.db = db
        self.marktplaats = MarktplaatsIntegration()
        self.vinted = VintedIntegration()
        self.depop = DepopIntegration()
        self.facebook = FacebookMarketplaceIntegration()
        self.sheets = GoogleSheetsService()

    def get_platform_integration(self, platform: Platform):
        """Get the appropriate platform integration"""
        integrations = {
            Platform.MARKTPLAATS: self.marktplaats,
            Platform.VINTED: self.vinted,
            Platform.DEPOP: self.depop,
            Platform.FACEBOOK_MARKETPLACE: self.facebook
        }
        return integrations.get(platform)

    async def sync_product_to_platform(
        self,
        product: Product,
        platform: Platform
    ) -> Optional[PlatformListing]:
        """
        Sync a product to a specific platform
        Creates a new listing if it doesn't exist, updates if it does
        """
        integration = self.get_platform_integration(platform)
        if not integration:
            return None

        # Check if listing already exists
        existing_listing = self.db.query(PlatformListing).filter(
            PlatformListing.product_id == product.id,
            PlatformListing.platform == platform
        ).first()

        product_data = {
            "title": product.title,
            "description": product.description,
            "price": product.price,
            "images": product.images,
            "category": product.category,
            "size": product.size,
            "condition": product.condition,
            "brand": product.brand,
            "color": product.color
        }

        try:
            if existing_listing and existing_listing.platform_listing_id:
                # Update existing listing
                success = await integration.update_listing(
                    existing_listing.platform_listing_id,
                    product_data
                )

                if success:
                    existing_listing.last_synced_at = datetime.now()
                    existing_listing.needs_sync = False
                    existing_listing.sync_error = None
                    self.db.commit()
                    return existing_listing
                else:
                    existing_listing.sync_error = "Failed to update listing"
                    self.db.commit()
                    return None
            else:
                # Create new listing
                platform_listing_id = await integration.create_listing(product_data)

                if platform_listing_id:
                    if existing_listing:
                        existing_listing.platform_listing_id = platform_listing_id
                        existing_listing.last_synced_at = datetime.now()
                        existing_listing.needs_sync = False
                        existing_listing.sync_error = None
                    else:
                        existing_listing = PlatformListing(
                            product_id=product.id,
                            platform=platform,
                            platform_listing_id=platform_listing_id,
                            platform_status=PlatformStatus.ACTIVE,
                            last_synced_at=datetime.now(),
                            needs_sync=False
                        )
                        self.db.add(existing_listing)

                    self.db.commit()
                    return existing_listing
                else:
                    if existing_listing:
                        existing_listing.sync_error = "Failed to create listing"
                        self.db.commit()
                    return None

        except Exception as e:
            print(f"Error syncing product {product.id} to {platform}: {e}")
            if existing_listing:
                existing_listing.sync_error = str(e)
                self.db.commit()
            return None

    async def cross_post_product(
        self,
        product: Product,
        platforms: List[Platform]
    ) -> Dict[Platform, Optional[PlatformListing]]:
        """
        Cross-post a product to multiple platforms
        """
        results = {}

        for platform in platforms:
            listing = await self.sync_product_to_platform(product, platform)
            results[platform] = listing

        return results

    async def mark_product_as_sold(
        self,
        product_id: int,
        sold_on_platform: Platform,
        sale_data: Optional[Dict[str, Any]] = None
    ):
        """
        Mark a product as sold and update all platforms + Google Sheets
        """
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return False

        # Update product status
        product.status = ProductStatus.SOLD
        self.db.commit()

        # Get all platform listings for this product
        listings = self.db.query(PlatformListing).filter(
            PlatformListing.product_id == product_id
        ).all()

        # Mark as sold on all platforms
        for listing in listings:
            integration = self.get_platform_integration(listing.platform)
            if integration and listing.platform_listing_id:
                try:
                    await integration.mark_as_sold(listing.platform_listing_id)
                    listing.platform_status = PlatformStatus.SOLD
                except Exception as e:
                    print(f"Error marking listing {listing.id} as sold: {e}")

        self.db.commit()

        # Create sale record
        if sale_data:
            sale = Sale(
                product_id=product_id,
                platform=sold_on_platform,
                sale_price=sale_data.get("sale_price", product.price),
                sale_date=sale_data.get("sale_date", datetime.now()),
                buyer_info=sale_data.get("buyer_info"),
                shipping_cost=sale_data.get("shipping_cost", 0),
                platform_fee=sale_data.get("platform_fee", 0),
                payment_fee=sale_data.get("payment_fee", 0)
            )

            # Calculate net profit
            original_cost = sale_data.get("original_cost", 0)
            sale.calculate_net_profit(original_cost)

            self.db.add(sale)
            self.db.commit()

            # Sync to Google Sheets
            await self.sync_sale_to_sheets(sale, product)

        return True

    async def sync_sale_to_sheets(self, sale: Sale, product: Product):
        """Sync a sale to Google Sheets"""
        try:
            sheets_data = {
                "sale_date": sale.sale_date.strftime("%Y-%m-%d %H:%M:%S"),
                "product_id": sale.product_id,
                "title": product.title,
                "platform": sale.platform.value,
                "sale_price": sale.sale_price,
                "original_cost": 0,  # You may want to track this separately
                "shipping_cost": sale.shipping_cost,
                "platform_fee": sale.platform_fee,
                "payment_fee": sale.payment_fee,
                "net_profit": sale.net_profit,
                "buyer_info": str(sale.buyer_info) if sale.buyer_info else "",
                "category": product.category,
                "brand": product.brand,
                "size": product.size
            }

            row_number = self.sheets.add_sale(sheets_data)

            if row_number:
                sale.synced_to_sheets = True
                sale.sheets_row_number = row_number
                self.db.commit()

        except Exception as e:
            print(f"Error syncing sale to Google Sheets: {e}")

    async def check_for_sold_items(self) -> List[Dict[str, Any]]:
        """
        Check all platforms for sold items and sync status
        """
        sold_items = []

        # Get all active products
        active_products = self.db.query(Product).filter(
            Product.status == ProductStatus.ACTIVE
        ).all()

        for product in active_products:
            listings = self.db.query(PlatformListing).filter(
                PlatformListing.product_id == product.id,
                PlatformListing.platform_status == PlatformStatus.ACTIVE
            ).all()

            for listing in listings:
                integration = self.get_platform_integration(listing.platform)
                if not integration or not listing.platform_listing_id:
                    continue

                try:
                    status = await integration.check_listing_status(listing.platform_listing_id)

                    if status == "sold":
                        # Mark as sold
                        await self.mark_product_as_sold(
                            product.id,
                            listing.platform,
                            {"sale_price": product.price, "sale_date": datetime.now()}
                        )

                        sold_items.append({
                            "product_id": product.id,
                            "title": product.title,
                            "platform": listing.platform.value
                        })

                        break  # No need to check other platforms

                except Exception as e:
                    print(f"Error checking listing status: {e}")

        return sold_items

    async def sync_all_products(self):
        """
        Full sync of all products that need syncing
        """
        listings = self.db.query(PlatformListing).filter(
            PlatformListing.needs_sync == True
        ).all()

        for listing in listings:
            product = listing.product
            await self.sync_product_to_platform(product, listing.platform)

    async def import_from_platform(self, platform: Platform) -> List[Product]:
        """
        Import existing listings from a platform into the CRM
        """
        integration = self.get_platform_integration(platform)
        if not integration:
            return []

        imported_products = []

        try:
            listings = await integration.get_listings()

            for listing_data in listings:
                # Check if product already exists based on platform listing ID
                existing_listing = self.db.query(PlatformListing).filter(
                    PlatformListing.platform == platform,
                    PlatformListing.platform_listing_id == listing_data.get("id")
                ).first()

                if existing_listing:
                    continue

                # Create new product
                product = Product(
                    title=listing_data.get("title", ""),
                    description=listing_data.get("description", ""),
                    price=listing_data.get("price", 0),
                    images=listing_data.get("images", []),
                    category=listing_data.get("category"),
                    size=listing_data.get("size"),
                    condition=listing_data.get("condition"),
                    brand=listing_data.get("brand"),
                    status=ProductStatus.ACTIVE
                )

                self.db.add(product)
                self.db.flush()

                # Create platform listing
                platform_listing = PlatformListing(
                    product_id=product.id,
                    platform=platform,
                    platform_listing_id=listing_data.get("id"),
                    listing_url=listing_data.get("url"),
                    platform_status=PlatformStatus.ACTIVE,
                    last_synced_at=datetime.now(),
                    needs_sync=False
                )

                self.db.add(platform_listing)
                imported_products.append(product)

            self.db.commit()

        except Exception as e:
            print(f"Error importing from {platform}: {e}")
            self.db.rollback()

        return imported_products

    async def cleanup(self):
        """Cleanup browser instances"""
        await self.vinted.close()
        await self.depop.close()
        await self.facebook.close()
