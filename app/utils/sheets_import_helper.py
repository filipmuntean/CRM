"""
Helper utilities for importing data from Google Sheets
Provides SKU matching, fuzzy title matching, and data parsing
"""

from typing import Dict, Any, Optional, Tuple
from fuzzywuzzy import fuzz
from sqlalchemy.orm import Session
from app.models.product import Product
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def match_product_by_sku(sku: str, db: Session) -> Optional[Product]:
    """
    Find a product by exact SKU match

    Args:
        sku: Product SKU to search for
        db: Database session

    Returns:
        Product if found, None otherwise
    """
    if not sku:
        return None

    return db.query(Product).filter(Product.sku == sku.strip()).first()


def fuzzy_match_product_by_title(
    title: str,
    db: Session,
    threshold: int = 85
) -> Tuple[Optional[Product], int]:
    """
    Find a product using fuzzy title matching

    Args:
        title: Product title to search for
        db: Database session
        threshold: Minimum similarity score (0-100) to consider a match

    Returns:
        Tuple of (Product if found, similarity score)
    """
    if not title:
        return None, 0

    # Get all products
    products = db.query(Product).all()

    best_match = None
    best_score = 0

    for product in products:
        # Calculate fuzzy match score
        score = fuzz.ratio(title.lower().strip(), product.title.lower().strip())

        if score > best_score and score >= threshold:
            best_score = score
            best_match = product

    return best_match, best_score


def parse_sheets_row_to_product(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a Google Sheets row to a Product dictionary

    Expected columns in row:
    - SKU, Title, Price, Original Cost, Category, Brand, Size, Condition, Status

    Args:
        row: Dictionary representing a row from Google Sheets

    Returns:
        Dictionary with product data ready for database insertion
    """
    try:
        product_data = {
            "sku": str(row.get("SKU", row.get("Product ID", ""))).strip(),
            "title": str(row.get("Title", "")).strip(),
            "price": float(row.get("Price", 0) or 0),
            "investment_per_product": float(row.get("Original Cost", 0) or 0),
            "category": str(row.get("Category", "")).strip() or None,
            "brand": str(row.get("Brand", "")).strip() or None,
            "size": str(row.get("Size", "")).strip() or None,
            "condition": str(row.get("Condition", "")).strip() or None,
            "status": str(row.get("Status", "active")).strip().lower(),
            "quantity": int(row.get("Quantity", 1) or 1),
        }

        # Validate required fields
        if not product_data["sku"] or not product_data["title"]:
            logger.warning(f"Row missing required fields: {row}")
            return None

        return product_data

    except Exception as e:
        logger.error(f"Error parsing product row: {e}, Row: {row}")
        return None


def parse_sheets_row_to_sale(row: Dict[str, Any], db: Session) -> Optional[Dict[str, Any]]:
    """
    Convert a Google Sheets row to a Sale dictionary

    Expected columns in row:
    - Date, SKU/Product ID, Title, Platform, Sale Price, Shipping Cost,
      Platform Fee, Payment Fee, VAT Amount, Original Cost, Notes

    Args:
        row: Dictionary representing a row from Google Sheets
        db: Database session (to match product by SKU)

    Returns:
        Dictionary with sale data ready for database insertion, or None if product not found
    """
    try:
        # Try to find the product by SKU first
        sku = str(row.get("SKU", row.get("Product ID", ""))).strip()
        product = match_product_by_sku(sku, db)

        # If not found by SKU, try fuzzy title match
        if not product:
            title = str(row.get("Title", "")).strip()
            product, match_score = fuzzy_match_product_by_title(title, db)

            if product and match_score < 95:
                logger.info(f"Fuzzy matched '{title}' to '{product.title}' (score: {match_score})")

        if not product:
            logger.warning(f"Could not find product for row: {row}")
            return None

        # Parse sale date
        sale_date_str = str(row.get("Date", row.get("Sale Date", ""))).strip()
        try:
            sale_date = datetime.strptime(sale_date_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                sale_date = datetime.strptime(sale_date_str, "%Y-%m-%d")
            except ValueError:
                logger.warning(f"Invalid date format: {sale_date_str}, using current time")
                sale_date = datetime.now()

        sale_data = {
            "product_id": product.id,
            "platform": str(row.get("Platform", "")).strip().lower(),
            "sale_price": float(row.get("Sale Price", 0) or 0),
            "sale_date": sale_date,
            "shipping_cost": float(row.get("Shipping Cost", 0) or 0),
            "platform_fee": float(row.get("Platform Fee", 0) or 0),
            "payment_fee": float(row.get("Payment Fee", 0) or 0),
            "vat_amount": float(row.get("VAT Amount", row.get("VAT", 0)) or 0),
            "original_cost": float(row.get("Original Cost", 0) or 0),
            "notes": str(row.get("Notes", "")).strip() or None,
        }

        # Calculate net profit
        sale_data["net_profit"] = (
            sale_data["sale_price"]
            - sale_data["shipping_cost"]
            - sale_data["platform_fee"]
            - sale_data["payment_fee"]
            - sale_data["vat_amount"]
            - sale_data["original_cost"]
        )

        return sale_data

    except Exception as e:
        logger.error(f"Error parsing sale row: {e}, Row: {row}")
        return None


def validate_product_data(product_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate product data before insertion

    Args:
        product_data: Product data dictionary

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not product_data.get("sku"):
        return False, "SKU is required"

    if not product_data.get("title"):
        return False, "Title is required"

    if product_data.get("price", 0) < 0:
        return False, "Price cannot be negative"

    return True, None


def validate_sale_data(sale_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate sale data before insertion

    Args:
        sale_data: Sale data dictionary

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not sale_data.get("product_id"):
        return False, "Product ID is required"

    if not sale_data.get("platform"):
        return False, "Platform is required"

    if sale_data.get("sale_price", 0) <= 0:
        return False, "Sale price must be greater than 0"

    return True, None
