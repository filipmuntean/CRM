import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.product import Product, ProductStatus
from app.models.sale import Sale
from app.utils.sheets_import_helper import (
    match_product_by_sku,
    fuzzy_match_product_by_title,
    parse_sheets_row_to_product,
    parse_sheets_row_to_sale,
    validate_product_data,
    validate_sale_data
)
import logging

logger = logging.getLogger(__name__)


class GoogleSheetsService:
    """Service for interacting with Google Sheets for accounting"""

    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    def __init__(self):
        self.credentials_file = settings.GOOGLE_SHEETS_CREDENTIALS_FILE
        self.spreadsheet_id = settings.GOOGLE_SHEETS_SPREADSHEET_ID
        self.client = None
        self.sheet = None

    def authenticate(self):
        """Authenticate with Google Sheets API"""
        try:
            creds = Credentials.from_service_account_file(
                self.credentials_file,
                scopes=self.SCOPES
            )
            self.client = gspread.authorize(creds)
            self.sheet = self.client.open_by_key(self.spreadsheet_id)
            return True
        except Exception as e:
            print(f"Error authenticating with Google Sheets: {e}")
            return False

    def get_or_create_sales_worksheet(self) -> Optional[gspread.Worksheet]:
        """Get or create the sales tracking worksheet"""
        try:
            if not self.sheet:
                self.authenticate()

            try:
                worksheet = self.sheet.worksheet("Sales")
            except gspread.WorksheetNotFound:
                # Create new worksheet with headers
                worksheet = self.sheet.add_worksheet(title="Sales", rows=1000, cols=15)
                headers = [
                    "Date",
                    "Product ID",
                    "Title",
                    "Platform",
                    "Sale Price",
                    "Original Cost",
                    "Shipping Cost",
                    "Platform Fee",
                    "Payment Fee",
                    "Net Profit",
                    "Buyer Info",
                    "Category",
                    "Brand",
                    "Size",
                    "Notes"
                ]
                worksheet.append_row(headers)

            return worksheet
        except Exception as e:
            print(f"Error getting/creating worksheet: {e}")
            return None

    def add_sale(self, sale_data: Dict[str, Any]) -> Optional[int]:
        """
        Add a sale to the Google Sheet
        Returns the row number if successful
        """
        try:
            worksheet = self.get_or_create_sales_worksheet()
            if not worksheet:
                return None

            # Prepare row data
            row = [
                sale_data.get("sale_date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                sale_data.get("product_id", ""),
                sale_data.get("title", ""),
                sale_data.get("platform", ""),
                sale_data.get("sale_price", 0),
                sale_data.get("original_cost", 0),
                sale_data.get("shipping_cost", 0),
                sale_data.get("platform_fee", 0),
                sale_data.get("payment_fee", 0),
                sale_data.get("net_profit", 0),
                str(sale_data.get("buyer_info", "")),
                sale_data.get("category", ""),
                sale_data.get("brand", ""),
                sale_data.get("size", ""),
                sale_data.get("notes", "")
            ]

            # Append row
            worksheet.append_row(row)

            # Get the row number (last row)
            row_number = len(worksheet.get_all_values())

            return row_number
        except Exception as e:
            print(f"Error adding sale to Google Sheets: {e}")
            return None

    def update_sale(self, row_number: int, sale_data: Dict[str, Any]) -> bool:
        """Update an existing sale row"""
        try:
            worksheet = self.get_or_create_sales_worksheet()
            if not worksheet:
                return False

            # Update specific cells
            updates = []
            if "sale_price" in sale_data:
                updates.append({"range": f"E{row_number}", "values": [[sale_data["sale_price"]]]})
            if "net_profit" in sale_data:
                updates.append({"range": f"J{row_number}", "values": [[sale_data["net_profit"]]]})

            if updates:
                worksheet.batch_update(updates)

            return True
        except Exception as e:
            print(f"Error updating sale in Google Sheets: {e}")
            return False

    def get_inventory_worksheet(self) -> Optional[gspread.Worksheet]:
        """Get or create the inventory tracking worksheet"""
        try:
            if not self.sheet:
                self.authenticate()

            try:
                worksheet = self.sheet.worksheet("Inventory")
            except gspread.WorksheetNotFound:
                worksheet = self.sheet.add_worksheet(title="Inventory", rows=1000, cols=12)
                headers = [
                    "Product ID",
                    "Title",
                    "Price",
                    "Original Cost",
                    "Category",
                    "Brand",
                    "Size",
                    "Condition",
                    "Status",
                    "Marktplaats",
                    "Vinted",
                    "Depop",
                    "Facebook Marketplace",
                    "Created Date",
                    "Updated Date"
                ]
                worksheet.append_row(headers)

            return worksheet
        except Exception as e:
            print(f"Error getting/creating inventory worksheet: {e}")
            return None

    def sync_product(self, product_data: Dict[str, Any]) -> bool:
        """Sync product information to inventory sheet"""
        try:
            worksheet = self.get_inventory_worksheet()
            if not worksheet:
                return False

            product_id = product_data.get("product_id")

            # Check if product already exists
            cell = worksheet.find(str(product_id), in_column=1)

            row = [
                product_id,
                product_data.get("title", ""),
                product_data.get("price", 0),
                product_data.get("original_cost", 0),
                product_data.get("category", ""),
                product_data.get("brand", ""),
                product_data.get("size", ""),
                product_data.get("condition", ""),
                product_data.get("status", ""),
                "Yes" if product_data.get("on_marktplaats") else "No",
                "Yes" if product_data.get("on_vinted") else "No",
                "Yes" if product_data.get("on_depop") else "No",
                "Yes" if product_data.get("on_facebook") else "No",
                product_data.get("created_at", ""),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ]

            if cell:
                # Update existing row
                worksheet.update(f"A{cell.row}:O{cell.row}", [row])
            else:
                # Add new row
                worksheet.append_row(row)

            return True
        except Exception as e:
            print(f"Error syncing product to Google Sheets: {e}")
            return False

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics from the sheets"""
        try:
            sales_worksheet = self.get_or_create_sales_worksheet()
            inventory_worksheet = self.get_inventory_worksheet()

            if not sales_worksheet or not inventory_worksheet:
                return {}

            # Get all sales data
            sales_data = sales_worksheet.get_all_records()

            # Calculate stats
            total_sales = len(sales_data)
            total_revenue = sum(float(row.get("Sale Price", 0)) for row in sales_data)
            total_profit = sum(float(row.get("Net Profit", 0)) for row in sales_data)

            # Platform breakdown
            platform_sales = {}
            for row in sales_data:
                platform = row.get("Platform", "Unknown")
                platform_sales[platform] = platform_sales.get(platform, 0) + 1

            # Inventory count
            inventory_data = inventory_worksheet.get_all_records()
            active_listings = sum(1 for row in inventory_data if row.get("Status") == "active")

            return {
                "total_sales": total_sales,
                "total_revenue": total_revenue,
                "total_profit": total_profit,
                "platform_sales": platform_sales,
                "active_listings": active_listings
            }
        except Exception as e:
            print(f"Error getting summary stats: {e}")
            return {}

    def import_inventory_with_sku_matching(
        self,
        db: Session,
        worksheet_name: str = "Sheet1"
    ) -> Dict[str, Any]:
        """
        Import inventory from Google Sheets with title matching (Romanian format)

        Returns:
            Dict with import results: matched, created, errors
        """
        try:
            if not self.sheet:
                self.authenticate()

            worksheet = self.sheet.worksheet(worksheet_name)
            all_rows = worksheet.get_all_records()

            results = {
                "matched": 0,
                "created": 0,
                "errors": [],
                "total_processed": 0
            }

            # Get unique product titles from rows without sale price (unsold inventory)
            unsold_products = {}
            for row in all_rows:
                sale_price = str(row.get("Preț Vanzare", "")).strip()

                # Skip if sold (has sale price)
                if sale_price and sale_price != "":
                    continue

                title = str(row.get("Coloana 3", "")).strip()
                if not title:
                    continue

                # Parse investment (handle comma decimal separator)
                investment_str = str(row.get("Investitie", "0")).replace(",", ".")
                try:
                    investment = float(investment_str) if investment_str else 0
                except:
                    investment = 0

                # Store unique products
                if title not in unsold_products:
                    unsold_products[title] = {
                        "title": title,
                        "investment": investment,
                        "purchase_date": row.get("Cand le-am cumparat", ""),
                        "posted_date": row.get("Cand le-am primit", "")
                    }

            # Process each unique product
            for title, product_info in unsold_products.items():
                results["total_processed"] += 1

                try:
                    # Check if product exists (fuzzy match by title)
                    existing_product, match_score = fuzzy_match_product_by_title(title, db, threshold=85)

                    if existing_product:
                        # Update existing product
                        existing_product.investment_per_product = product_info["investment"]
                        existing_product.status = ProductStatus.ACTIVE
                        db.commit()
                        results["matched"] += 1
                        logger.info(f"Matched product: {title} (score: {match_score})")
                    else:
                        # Create new product - generate SKU from title
                        sku = self._generate_sku_from_title(title, db)

                        new_product = Product(
                            sku=sku,
                            title=title,
                            price=0,  # Will be set when listing
                            investment_per_product=product_info["investment"],
                            status=ProductStatus.ACTIVE,
                            quantity=1
                        )
                        db.add(new_product)
                        db.commit()
                        results["created"] += 1
                        logger.info(f"Created new product: {title} with SKU: {sku}")

                except Exception as e:
                    results["errors"].append({
                        "title": title,
                        "error": str(e)
                    })
                    logger.error(f"Error processing product {title}: {e}")
                    db.rollback()

            return results

        except Exception as e:
            logger.error(f"Error importing inventory: {e}")
            return {
                "matched": 0,
                "created": 0,
                "errors": [{"error": str(e)}],
                "total_processed": 0
            }

    def import_historical_sales(
        self,
        db: Session,
        worksheet_name: str = "Sheet1"
    ) -> Dict[str, Any]:
        """
        Import historical sales data from Google Sheets (Romanian format)

        Returns:
            Dict with import results
        """
        try:
            if not self.sheet:
                self.authenticate()

            worksheet = self.sheet.worksheet(worksheet_name)
            all_rows = worksheet.get_all_records()

            results = {
                "imported": 0,
                "skipped": 0,
                "errors": [],
                "total_processed": 0
            }

            for row in all_rows:
                results["total_processed"] += 1

                # Only process rows with sale price
                sale_price_str = str(row.get("Preț Vanzare", "")).strip()
                if not sale_price_str or sale_price_str == "":
                    results["skipped"] += 1
                    continue

                try:
                    # Parse sale price (handle comma decimal)
                    sale_price = float(sale_price_str.replace(",", "."))

                    # Skip if invalid sale price
                    if sale_price <= 0:
                        results["skipped"] += 1
                        continue

                    # Get product title and find/create product
                    title = str(row.get("Coloana 3", "")).strip()
                    if not title:
                        results["errors"].append({"row": results["total_processed"], "error": "Missing title"})
                        continue

                    # Find or create product
                    product = self._find_or_create_product(title, row, db)
                    if not product:
                        results["errors"].append({"row": results["total_processed"], "error": f"Could not find/create product: {title}"})
                        continue

                    # Parse sale date (Romanian format: d.M.yyyy)
                    sale_date_str = str(row.get("Data vanzare", "")).strip()
                    sale_date = self._parse_romanian_date(sale_date_str)

                    if not sale_date:
                        results["errors"].append({"row": results["total_processed"], "error": f"Invalid date: {sale_date_str}"})
                        continue

                    # Parse other fields
                    profit_str = str(row.get("Profit", "0")).replace(",", ".")
                    profit = float(profit_str) if profit_str else 0

                    vat_str = str(row.get("VAT", "0")).replace(",", ".")
                    vat = float(vat_str) if vat_str else 0

                    investment_str = str(row.get("Investitie", "0")).replace(",", ".")
                    investment = float(investment_str) if investment_str else 0

                    # Determine platform (if VAT present, likely Vinted)
                    platform = "vinted" if vat > 0 else "unknown"

                    # Check if sale already exists
                    existing_sale = db.query(Sale).filter(
                        Sale.product_id == product.id,
                        Sale.sale_date == sale_date,
                        Sale.sale_price == sale_price
                    ).first()

                    if existing_sale:
                        results["skipped"] += 1
                        continue

                    # Create new sale
                    new_sale = Sale(
                        product_id=product.id,
                        platform=platform,
                        sale_price=sale_price,
                        sale_date=sale_date,
                        vat_amount=vat,
                        original_cost=investment,
                        net_profit=profit,
                        shipping_cost=0,  # Not in your sheet
                        platform_fee=0,   # Not in your sheet
                        payment_fee=0,    # Not in your sheet
                        synced_to_sheets=True
                    )

                    db.add(new_sale)
                    db.commit()

                    # Update product status to SOLD
                    product.status = ProductStatus.SOLD
                    db.commit()

                    results["imported"] += 1

                except Exception as e:
                    results["errors"].append({
                        "row": results["total_processed"],
                        "title": row.get("Coloana 3", ""),
                        "error": str(e)
                    })
                    logger.error(f"Error importing sale: {e}")
                    db.rollback()

            return results

        except Exception as e:
            logger.error(f"Error importing sales: {e}")
            return {
                "imported": 0,
                "skipped": 0,
                "errors": [{"error": str(e)}],
                "total_processed": 0
            }

    def _generate_sku_from_title(self, title: str, db: Session) -> str:
        """Generate a unique SKU from product title"""
        import re

        # Clean title and create base SKU
        clean_title = re.sub(r'[^a-zA-Z0-9]', '', title.lower())
        base_sku = clean_title[:10].upper()

        # Add number if SKU exists
        counter = 1
        sku = base_sku

        while db.query(Product).filter(Product.sku == sku).first():
            sku = f"{base_sku}{counter}"
            counter += 1

        return sku

    def _parse_romanian_date(self, date_str: str) -> Optional[datetime]:
        """Parse Romanian date format (d.M.yyyy or dd.MM.yyyy)"""
        if not date_str or date_str.strip() == "":
            return None

        try:
            # Try various date formats
            for fmt in ["%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d", "%d/%m/%Y"]:
                try:
                    return datetime.strptime(date_str.strip(), fmt)
                except ValueError:
                    continue

            logger.warning(f"Could not parse date: {date_str}")
            return None

        except Exception as e:
            logger.error(f"Error parsing date {date_str}: {e}")
            return None

    def _find_or_create_product(self, title: str, row: Dict, db: Session) -> Optional[Product]:
        """Find existing product by title or create new one"""
        try:
            # Try fuzzy match first
            product, match_score = fuzzy_match_product_by_title(title, db, threshold=85)

            if product:
                return product

            # Create new product if not found
            investment_str = str(row.get("Investitie", "0")).replace(",", ".")
            investment = float(investment_str) if investment_str else 0

            sku = self._generate_sku_from_title(title, db)

            new_product = Product(
                sku=sku,
                title=title,
                price=0,
                investment_per_product=investment,
                status=ProductStatus.SOLD,
                quantity=1
            )

            db.add(new_product)
            db.commit()
            db.refresh(new_product)

            return new_product

        except Exception as e:
            logger.error(f"Error finding/creating product {title}: {e}")
            return None
