from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.core.database import get_db
from app.models.platform_listing import Platform
from app.services.sync_service import SyncService

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/import/{platform}")
async def import_from_platform(
    platform: Platform,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Import existing listings from a platform"""
    sync_service = SyncService(db)

    try:
        products = await sync_service.import_from_platform(platform)

        # Cleanup browsers in background
        background_tasks.add_task(sync_service.cleanup)

        return {
            "message": f"Successfully imported {len(products)} products from {platform.value}",
            "count": len(products),
            "product_ids": [p.id for p in products]
        }
    except Exception as e:
        await sync_service.cleanup()
        return {"error": str(e)}


@router.post("/check-sold")
async def check_sold_items(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Check all platforms for sold items and sync status"""
    sync_service = SyncService(db)

    try:
        sold_items = await sync_service.check_for_sold_items()

        # Cleanup browsers in background
        background_tasks.add_task(sync_service.cleanup)

        return {
            "message": f"Found {len(sold_items)} sold items",
            "sold_items": sold_items
        }
    except Exception as e:
        await sync_service.cleanup()
        return {"error": str(e)}


@router.post("/all")
async def sync_all_products(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Sync all products that need syncing"""
    sync_service = SyncService(db)

    try:
        await sync_service.sync_all_products()

        # Cleanup browsers in background
        background_tasks.add_task(sync_service.cleanup)

        return {"message": "All products synced successfully"}
    except Exception as e:
        await sync_service.cleanup()
        return {"error": str(e)}


@router.get("/stats")
def get_sync_stats(db: Session = Depends(get_db)):
    """Get synchronization statistics"""
    from app.models.platform_listing import PlatformListing

    total_listings = db.query(PlatformListing).count()
    needs_sync = db.query(PlatformListing).filter(PlatformListing.needs_sync == True).count()
    has_errors = db.query(PlatformListing).filter(PlatformListing.sync_error != None).count()

    # Platform breakdown
    from sqlalchemy import func
    platform_counts = db.query(
        PlatformListing.platform,
        func.count(PlatformListing.id)
    ).group_by(PlatformListing.platform).all()

    return {
        "total_listings": total_listings,
        "needs_sync": needs_sync,
        "has_errors": has_errors,
        "by_platform": {platform.value: count for platform, count in platform_counts}
    }
