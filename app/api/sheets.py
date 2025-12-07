"""
Google Sheets import/export API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.core.database import get_db
from app.services.sheets_service import GoogleSheetsService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sheets", tags=["sheets"])


@router.post("/import/inventory")
async def import_inventory(
    worksheet_name: str = Query("Sheet1", description="Name of the worksheet to import from"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Import inventory from Google Sheets with title matching

    Processes rows without sale prices as current inventory.
    Creates or updates products based on fuzzy title matching.
    """
    try:
        sheets_service = GoogleSheetsService()

        if not sheets_service.authenticate():
            raise HTTPException(status_code=500, detail="Failed to authenticate with Google Sheets")

        results = sheets_service.import_inventory_with_sku_matching(db, worksheet_name)

        return {
            "success": True,
            "message": f"Imported {results['created']} new products, matched {results['matched']} existing products",
            "results": results
        }

    except Exception as e:
        logger.error(f"Error importing inventory: {e}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/import/sales")
async def import_sales(
    worksheet_name: str = Query("Sheet1", description="Name of the worksheet to import from"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Import historical sales data from Google Sheets

    Processes rows with sale prices as historical sales.
    Automatically matches products by title or creates new ones.
    Detects platform based on VAT presence (Vinted if VAT > 0).
    """
    try:
        sheets_service = GoogleSheetsService()

        if not sheets_service.authenticate():
            raise HTTPException(status_code=500, detail="Failed to authenticate with Google Sheets")

        results = sheets_service.import_historical_sales(db, worksheet_name)

        return {
            "success": True,
            "message": f"Imported {results['imported']} sales, skipped {results['skipped']} duplicates",
            "results": results
        }

    except Exception as e:
        logger.error(f"Error importing sales: {e}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/import/all")
async def import_all(
    worksheet_name: str = Query("Sheet1", description="Name of the worksheet to import from"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Import both inventory and sales in one operation

    First imports inventory (unsold items), then imports sales history.
    """
    try:
        sheets_service = GoogleSheetsService()

        if not sheets_service.authenticate():
            raise HTTPException(status_code=500, detail="Failed to authenticate with Google Sheets")

        # Import inventory first
        inventory_results = sheets_service.import_inventory_with_sku_matching(db, worksheet_name)

        # Then import sales
        sales_results = sheets_service.import_historical_sales(db, worksheet_name)

        return {
            "success": True,
            "message": f"Imported {inventory_results['created']} products and {sales_results['imported']} sales",
            "inventory_results": inventory_results,
            "sales_results": sales_results
        }

    except Exception as e:
        logger.error(f"Error importing all data: {e}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.get("/preview")
async def preview_import(
    worksheet_name: str = Query("Sheet1", description="Name of the worksheet to preview"),
) -> Dict[str, Any]:
    """
    Preview what will be imported without actually importing

    Returns counts and sample data from the Google Sheet.
    """
    try:
        sheets_service = GoogleSheetsService()

        if not sheets_service.authenticate():
            raise HTTPException(status_code=500, detail="Failed to authenticate with Google Sheets")

        worksheet = sheets_service.sheet.worksheet(worksheet_name)
        all_rows = worksheet.get_all_records()

        # Count sold vs unsold
        sold_count = 0
        unsold_count = 0
        unique_titles = set()

        for row in all_rows:
            sale_price = str(row.get("Preț Vanzare", "")).strip()
            title = str(row.get("Coloana 3", "")).strip()

            if title:
                unique_titles.add(title)

            if sale_price and sale_price != "":
                sold_count += 1
            else:
                unsold_count += 1

        # Get sample rows
        sample_sold = []
        sample_unsold = []

        for row in all_rows[:10]:
            sale_price = str(row.get("Preț Vanzare", "")).strip()
            if sale_price and sale_price != "" and len(sample_sold) < 3:
                sample_sold.append({
                    "title": row.get("Coloana 3", ""),
                    "sale_price": sale_price,
                    "profit": row.get("Profit", ""),
                    "vat": row.get("VAT", ""),
                    "sale_date": row.get("Data vanzare", "")
                })
            elif not sale_price and len(sample_unsold) < 3:
                sample_unsold.append({
                    "title": row.get("Coloana 3", ""),
                    "investment": row.get("Investitie", ""),
                    "purchase_date": row.get("Cand le-am cumparat", "")
                })

        return {
            "success": True,
            "total_rows": len(all_rows),
            "sold_items": sold_count,
            "unsold_items": unsold_count,
            "unique_products": len(unique_titles),
            "sample_sold_items": sample_sold,
            "sample_unsold_items": sample_unsold,
            "message": f"Found {sold_count} sales and {unsold_count} unsold items across {len(unique_titles)} unique products"
        }

    except Exception as e:
        logger.error(f"Error previewing import: {e}")
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")
