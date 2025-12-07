from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import time
from app.core.database import get_db
from app.models.product import Product, ProductStatus
from app.models.platform_listing import Platform
from app.schemas.product import Product as ProductSchema, ProductCreate, ProductUpdate, ProductWithListings
from app.services.sync_service import SyncService
from app.utils.product_utils import generate_sku, calculate_investment

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/", response_model=List[ProductSchema])
def get_products(
    skip: int = 0,
    limit: int = 100,
    status: Optional[ProductStatus] = None,
    db: Session = Depends(get_db)
):
    """Get all products"""
    query = db.query(Product)

    if status:
        query = query.filter(Product.status == status)

    products = query.offset(skip).limit(limit).all()
    return products


@router.get("/{product_id}", response_model=ProductWithListings)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get a specific product with its platform listings"""
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return product


@router.post("/", response_model=ProductSchema)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    """Create a new product"""
    # Convert product to dict and remove investment_calculation field
    product_data = product.dict(exclude={"investment_calculation"})

    # Generate unique SKU
    sku = generate_sku(product.title, product.category)

    # Ensure SKU is unique
    while db.query(Product).filter(Product.sku == sku).first():
        sku = generate_sku(product.title + str(time.time()), product.category)

    product_data["sku"] = sku

    # Calculate investment if expression provided
    if product.investment_calculation:
        try:
            product_data["investment_per_product"] = calculate_investment(product.investment_calculation)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    db_product = Product(**product_data)
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


@router.put("/{product_id}", response_model=ProductSchema)
def update_product(
    product_id: int,
    product_update: ProductUpdate,
    db: Session = Depends(get_db)
):
    """Update a product"""
    db_product = db.query(Product).filter(Product.id == product_id).first()

    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Get update data and exclude investment_calculation field
    update_data = product_update.dict(exclude_unset=True, exclude={"investment_calculation"})

    # Calculate investment if expression provided
    if product_update.investment_calculation is not None:
        try:
            update_data["investment_per_product"] = calculate_investment(product_update.investment_calculation)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Update fields
    for field, value in update_data.items():
        setattr(db_product, field, value)

    # Mark all platform listings as needing sync
    for listing in db_product.platform_listings:
        listing.needs_sync = True

    db.commit()
    db.refresh(db_product)
    return db_product


@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """Delete a product"""
    db_product = db.query(Product).filter(Product.id == product_id).first()

    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    db.delete(db_product)
    db.commit()
    return {"message": "Product deleted successfully"}


@router.post("/{product_id}/cross-post")
async def cross_post_product(
    product_id: int,
    platforms: List[Platform],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Cross-post a product to multiple platforms"""
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    sync_service = SyncService(db)

    try:
        results = await sync_service.cross_post_product(product, platforms)

        # Cleanup browsers in background
        background_tasks.add_task(sync_service.cleanup)

        return {
            "product_id": product_id,
            "results": {
                platform.value: {
                    "success": listing is not None,
                    "listing_id": listing.platform_listing_id if listing else None
                }
                for platform, listing in results.items()
            }
        }
    except Exception as e:
        await sync_service.cleanup()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{product_id}/sync/{platform}")
async def sync_product_to_platform(
    product_id: int,
    platform: Platform,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Sync a product to a specific platform"""
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    sync_service = SyncService(db)

    try:
        listing = await sync_service.sync_product_to_platform(product, platform)

        # Cleanup browsers in background
        background_tasks.add_task(sync_service.cleanup)

        if listing:
            return {
                "success": True,
                "listing_id": listing.platform_listing_id,
                "platform": platform.value
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to sync product")

    except Exception as e:
        await sync_service.cleanup()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{product_id}/mark-sold")
async def mark_product_sold(
    product_id: int,
    platform: Platform,
    background_tasks: BackgroundTasks,
    sale_price: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """Mark a product as sold on a specific platform"""
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    sync_service = SyncService(db)

    try:
        from datetime import datetime

        sale_data = {
            "sale_price": sale_price or product.price,
            "sale_date": datetime.now()
        }

        success = await sync_service.mark_product_as_sold(product_id, platform, sale_data)

        # Cleanup browsers in background
        background_tasks.add_task(sync_service.cleanup)

        if success:
            return {"message": "Product marked as sold successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to mark product as sold")

    except Exception as e:
        await sync_service.cleanup()
        raise HTTPException(status_code=500, detail=str(e))
