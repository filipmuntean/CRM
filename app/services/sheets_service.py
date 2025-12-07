import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.core.config import settings


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
