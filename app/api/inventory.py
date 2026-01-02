from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import List, Optional
from datetime import date, datetime
from pydantic import BaseModel
from app.core.database import get_db
from app.models.product import Product, ProductStatus, Batch, Expense, RecurringExpense, ExpenseFrequency

router = APIRouter(prefix="/inventory", tags=["inventory"])


# Pydantic schemas
class InventoryItemCreate(BaseModel):
    title: str
    purchase_date: Optional[str] = None  # Accept string, parse later
    received_date: Optional[str] = None
    purchase_cost: float
    batch_name: Optional[str] = None
    sale_price: Optional[float] = None
    sale_date: Optional[str] = None
    vat_amount: Optional[float] = None
    batch_id: Optional[int] = None
    payment_installments: Optional[int] = 1  # 1 = paid in full, 4 = 4 monthly payments


class InventoryItemUpdate(BaseModel):
    title: Optional[str] = None
    purchase_date: Optional[str] = None
    received_date: Optional[str] = None
    purchase_cost: Optional[float] = None
    batch_name: Optional[str] = None
    sale_price: Optional[float] = None
    sale_date: Optional[str] = None
    vat_amount: Optional[float] = None
    status: Optional[str] = None
    payment_installments: Optional[int] = None


class InventoryItemResponse(BaseModel):
    id: int
    title: str
    purchase_date: Optional[date]
    received_date: Optional[date]
    purchase_cost: Optional[float]
    batch_name: Optional[str]  # Product name/description
    batch_id: Optional[int]  # Batch group ID
    batch_group: Optional[str]  # Batch group name (from Batch model)
    sale_price: Optional[float]
    sale_date: Optional[date]
    vat_amount: Optional[float]
    profit: float
    days_to_sell: int
    status: str
    payment_installments: int = 1

    class Config:
        from_attributes = True


class BulkAddRequest(BaseModel):
    batch_name: str
    total_cost: float
    item_count: int
    purchase_date: Optional[date] = None
    received_date: Optional[date] = None
    notes: Optional[str] = None


class BatchResponse(BaseModel):
    id: int
    name: str
    total_cost: float
    item_count: int
    cost_per_item: float
    purchase_date: Optional[date]
    items_sold: int
    total_revenue: float
    total_profit: float
    roi: float
    batch_expenses: float = 0  # Expenses linked to this batch
    total_investment: float = 0  # total_cost + batch_expenses

    class Config:
        from_attributes = True


class ExpenseCreate(BaseModel):
    amount: float
    category: str
    description: Optional[str] = None
    expense_date: str  # Accept string, parse later
    batch_id: Optional[int] = None  # Optional link to batch


class ExpenseResponse(BaseModel):
    id: int
    amount: float
    category: str
    description: Optional[str]
    expense_date: date
    batch_id: Optional[int] = None
    batch_name: Optional[str] = None

    class Config:
        from_attributes = True


class MonthlyStats(BaseModel):
    month: str
    year: int
    revenue: float
    profit: float  # Gross profit (sale_price - purchase_cost)
    net_profit: float  # Net profit (gross profit - expenses)
    cashflow: float
    items_sold: int
    expenses: float


class DashboardStats(BaseModel):
    total_revenue: float
    total_profit: float
    total_items_sold: int
    total_items_unsold: int
    total_investment: float
    avg_profit_per_item: float
    avg_days_to_sell: float
    # New metrics
    roi: float  # Return on Investment %
    profit_margin: float  # Profit Margin %
    unsold_stock_value: float  # Value of unsold inventory
    total_expenses: float  # All expenses (one-time + recurring)
    net_profit: float  # Profit after expenses
    sell_through_rate: float  # % of items sold
    avg_sale_price: float  # Average selling price
    avg_purchase_cost: float  # Average cost per item
    # This month stats
    this_month_revenue: float
    this_month_profit: float
    this_month_items_sold: int


# Paginated response model
class PaginatedInventoryResponse(BaseModel):
    items: List[InventoryItemResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


# Inventory endpoints
@router.get("/items", response_model=PaginatedInventoryResponse)
def get_inventory_items(
    status: Optional[str] = None,
    batch_name: Optional[str] = None,
    page: int = 1,
    per_page: int = 100,
    db: Session = Depends(get_db)
):
    """Get all inventory items with optional filtering and pagination"""
    query = db.query(Product)

    if status:
        query = query.filter(Product.status == status)
    if batch_name:
        query = query.filter(Product.batch_name == batch_name)

    # Get total count
    total = query.count()
    total_pages = (total + per_page - 1) // per_page  # Ceiling division

    # Get paginated items
    skip = (page - 1) * per_page
    items = query.order_by(Product.purchase_date.desc()).offset(skip).limit(per_page).all()

    return PaginatedInventoryResponse(
        items=[
            InventoryItemResponse(
                id=item.id,
                title=item.title,
                purchase_date=item.purchase_date,
                received_date=item.received_date,
                purchase_cost=item.purchase_cost,
                batch_name=item.batch_name,
                batch_id=item.batch_id,
                batch_group=item.batch.name if item.batch else None,
                sale_price=item.sale_price,
                sale_date=item.sale_date,
                vat_amount=item.vat_amount,
                profit=item.profit,
                days_to_sell=item.days_to_sell,
                status=item.status.value,
                payment_installments=item.payment_installments or 1
            )
            for item in items
        ],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )


def parse_date_string(date_str: Optional[str]) -> Optional[date]:
    """Parse various date formats to date object"""
    if not date_str or date_str.strip() == '':
        return None
    date_str = date_str.strip()

    # Try ISO format first (YYYY-MM-DD)
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except:
        pass

    # Try European format with dots (D.M.YYYY or DD.MM.YYYY)
    try:
        parts = date_str.split('.')
        if len(parts) == 3:
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            return date(year, month, day)
    except:
        pass

    # Try format with commas (D,M,YYYY or DD,MM,YYYY)
    try:
        parts = date_str.split(',')
        if len(parts) == 3:
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            return date(year, month, day)
    except:
        pass

    # Try slash format (D/M/YYYY)
    try:
        parts = date_str.split('/')
        if len(parts) == 3:
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            return date(year, month, day)
    except:
        pass

    # Try dash format (D-M-YYYY)
    try:
        parts = date_str.split('-')
        if len(parts) == 3:
            # Check if it's YYYY-MM-DD or DD-MM-YYYY
            if len(parts[0]) == 4:
                year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
            else:
                day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            return date(year, month, day)
    except:
        pass

    return None


@router.post("/items", response_model=InventoryItemResponse)
def create_inventory_item(item: InventoryItemCreate, db: Session = Depends(get_db)):
    """Create a single inventory item"""
    # Parse dates
    purchase_date = parse_date_string(item.purchase_date)
    received_date = parse_date_string(item.received_date)
    sale_date = parse_date_string(item.sale_date)

    status = ProductStatus.SOLD if sale_date else ProductStatus.ACTIVE

    db_item = Product(
        title=item.title,
        price=item.sale_price or item.purchase_cost,
        purchase_date=purchase_date,
        received_date=received_date,
        purchase_cost=item.purchase_cost,
        batch_name=item.batch_name,
        sale_price=item.sale_price,
        sale_date=sale_date,
        vat_amount=item.vat_amount,
        batch_id=item.batch_id,
        payment_installments=item.payment_installments or 1,
        status=status
    )

    db.add(db_item)
    db.commit()
    db.refresh(db_item)

    return InventoryItemResponse(
        id=db_item.id,
        title=db_item.title,
        purchase_date=db_item.purchase_date,
        received_date=db_item.received_date,
        purchase_cost=db_item.purchase_cost,
        batch_name=db_item.batch_name,
        sale_price=db_item.sale_price,
        sale_date=db_item.sale_date,
        vat_amount=db_item.vat_amount,
        profit=db_item.profit,
        days_to_sell=db_item.days_to_sell,
        status=db_item.status.value,
        payment_installments=db_item.payment_installments or 1
    )


@router.put("/items/{item_id}", response_model=InventoryItemResponse)
def update_inventory_item(item_id: int, item: InventoryItemUpdate, db: Session = Depends(get_db)):
    """Update an inventory item (inline editing)"""
    db_item = db.query(Product).filter(Product.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")

    update_data = item.dict(exclude_unset=True)

    # Parse date fields
    for date_field in ['purchase_date', 'received_date', 'sale_date']:
        if date_field in update_data:
            update_data[date_field] = parse_date_string(update_data[date_field])

    # Auto-update status based on sale_date
    if "sale_date" in update_data:
        if update_data["sale_date"]:
            update_data["status"] = ProductStatus.SOLD
        else:
            update_data["status"] = ProductStatus.ACTIVE
    elif "status" in update_data:
        update_data["status"] = ProductStatus(update_data["status"])

    for key, value in update_data.items():
        setattr(db_item, key, value)

    db.commit()
    db.refresh(db_item)

    return InventoryItemResponse(
        id=db_item.id,
        title=db_item.title,
        purchase_date=db_item.purchase_date,
        received_date=db_item.received_date,
        purchase_cost=db_item.purchase_cost,
        batch_name=db_item.batch_name,
        sale_price=db_item.sale_price,
        sale_date=db_item.sale_date,
        vat_amount=db_item.vat_amount,
        profit=db_item.profit,
        days_to_sell=db_item.days_to_sell,
        status=db_item.status.value,
        payment_installments=db_item.payment_installments or 1
    )


@router.delete("/items/{item_id}")
def delete_inventory_item(item_id: int, db: Session = Depends(get_db)):
    """Delete an inventory item"""
    db_item = db.query(Product).filter(Product.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")

    db.delete(db_item)
    db.commit()
    return {"message": "Item deleted"}


@router.delete("/items")
def delete_multiple_items(item_ids: List[int], db: Session = Depends(get_db)):
    """Delete multiple inventory items"""
    db.query(Product).filter(Product.id.in_(item_ids)).delete(synchronize_session=False)
    db.commit()
    return {"message": f"Deleted {len(item_ids)} items"}


@router.get("/batch-groups")
def get_batch_groups(db: Session = Depends(get_db)):
    """Get all batch groups"""
    batches = db.query(Batch).order_by(Batch.name).all()
    return [{"id": b.id, "name": b.name} for b in batches]


class BatchAssignRequest(BaseModel):
    item_ids: Optional[List[int]] = None
    batch_id: Optional[int] = None  # Existing batch ID
    batch_name: Optional[str] = None  # New batch name (creates new batch)
    all_items: bool = False
    status_filter: Optional[str] = None
    batch_filter: Optional[int] = None  # Filter by batch_id


@router.post("/items/assign-batch")
def assign_items_to_batch(request: BatchAssignRequest, db: Session = Depends(get_db)):
    """Assign multiple items to a batch group"""
    # Get or create batch
    if request.batch_id:
        batch = db.query(Batch).filter(Batch.id == request.batch_id).first()
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
        batch_id = batch.id
        batch_name = batch.name
    elif request.batch_name:
        # Create new batch
        batch = Batch(
            name=request.batch_name,
            total_cost=0,
            item_count=0
        )
        db.add(batch)
        db.flush()  # Get the ID
        batch_id = batch.id
        batch_name = batch.name
    else:
        raise HTTPException(status_code=400, detail="batch_id or batch_name required")

    if request.all_items:
        query = db.query(Product)
        if request.status_filter:
            query = query.filter(Product.status == request.status_filter)
        if request.batch_filter:
            query = query.filter(Product.batch_id == request.batch_filter)
        count = query.update({Product.batch_id: batch_id}, synchronize_session=False)
        db.commit()
        return {"message": f"Assigned {count} items to batch '{batch_name}'"}
    else:
        db.query(Product).filter(Product.id.in_(request.item_ids)).update(
            {Product.batch_id: batch_id},
            synchronize_session=False
        )
        db.commit()
        return {"message": f"Assigned {len(request.item_ids)} items to batch '{batch_name}'"}


# Bulk add (batch) endpoints
@router.post("/bulk-add", response_model=BatchResponse)
def bulk_add_items(request: BulkAddRequest, db: Session = Depends(get_db)):
    """Add a batch of items (e.g., 100 items for €700 = €7 each)"""
    # Create the batch
    batch = Batch(
        name=request.batch_name,
        total_cost=request.total_cost,
        item_count=request.item_count,
        purchase_date=request.purchase_date,
        received_date=request.received_date,
        notes=request.notes
    )
    db.add(batch)
    db.flush()

    cost_per_item = request.total_cost / request.item_count

    # Create individual items
    for i in range(request.item_count):
        item = Product(
            title=f"{request.batch_name} #{i+1}",
            price=cost_per_item,
            purchase_date=request.purchase_date,
            received_date=request.received_date,
            purchase_cost=cost_per_item,
            batch_name=request.batch_name,
            batch_id=batch.id,
            status=ProductStatus.ACTIVE
        )
        db.add(item)

    db.commit()
    db.refresh(batch)

    return BatchResponse(
        id=batch.id,
        name=batch.name,
        total_cost=batch.total_cost,
        item_count=batch.item_count,
        cost_per_item=batch.cost_per_item,
        purchase_date=batch.purchase_date,
        items_sold=batch.items_sold,
        total_revenue=batch.total_revenue,
        total_profit=batch.total_profit,
        roi=batch.roi
    )


@router.get("/batches", response_model=List[BatchResponse])
def get_batches(db: Session = Depends(get_db)):
    """Get all batches with their stats"""
    batches = db.query(Batch).all()
    return [
        BatchResponse(
            id=b.id,
            name=b.name,
            total_cost=b.total_cost,
            item_count=b.item_count,
            cost_per_item=b.cost_per_item,
            purchase_date=b.purchase_date,
            items_sold=b.items_sold,
            total_revenue=b.total_revenue,
            total_profit=b.total_profit,
            roi=b.roi,
            batch_expenses=b.batch_expenses,
            total_investment=b.total_investment
        )
        for b in batches
    ]


# Expense endpoints
@router.post("/expenses", response_model=ExpenseResponse)
def create_expense(expense: ExpenseCreate, db: Session = Depends(get_db)):
    """Add an expense"""
    db_expense = Expense(
        amount=expense.amount,
        category=expense.category,
        description=expense.description,
        expense_date=parse_date_string(expense.expense_date),
        batch_id=expense.batch_id
    )
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)

    return ExpenseResponse(
        id=db_expense.id,
        amount=db_expense.amount,
        category=db_expense.category,
        description=db_expense.description,
        expense_date=db_expense.expense_date,
        batch_id=db_expense.batch_id,
        batch_name=db_expense.batch.name if db_expense.batch else None
    )


@router.get("/expenses", response_model=List[ExpenseResponse])
def get_expenses(
    category: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    batch_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get expenses with optional filtering"""
    query = db.query(Expense)

    if category:
        query = query.filter(Expense.category == category)
    if start_date:
        query = query.filter(Expense.expense_date >= start_date)
    if end_date:
        query = query.filter(Expense.expense_date <= end_date)
    if batch_id:
        query = query.filter(Expense.batch_id == batch_id)

    expenses = query.order_by(Expense.expense_date.desc()).all()

    return [
        ExpenseResponse(
            id=e.id,
            amount=e.amount,
            category=e.category,
            description=e.description,
            expense_date=e.expense_date,
            batch_id=e.batch_id,
            batch_name=e.batch.name if e.batch else None
        )
        for e in expenses
    ]


@router.delete("/expenses/{expense_id}")
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    """Delete an expense"""
    db_expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not db_expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    db.delete(db_expense)
    db.commit()
    return {"message": "Expense deleted"}


# Financial stats endpoints
@router.get("/stats/dashboard", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get overall dashboard statistics"""
    sold_items = db.query(Product).filter(Product.status == ProductStatus.SOLD).all()
    unsold_items = db.query(Product).filter(Product.status == ProductStatus.ACTIVE).all()
    all_items = sold_items + unsold_items

    total_revenue = sum(p.sale_price or 0 for p in sold_items)
    total_profit = sum(p.profit for p in sold_items)
    total_investment = sum(p.purchase_cost or 0 for p in all_items)
    unsold_stock_value = sum(p.purchase_cost or 0 for p in unsold_items)

    days_list = [p.days_to_sell for p in sold_items if p.days_to_sell > 0]
    avg_days = sum(days_list) / len(days_list) if days_list else 0

    # Calculate ROI and profit margin
    roi = (total_profit / total_investment * 100) if total_investment > 0 else 0
    profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0

    # Sell-through rate
    total_items = len(sold_items) + len(unsold_items)
    sell_through_rate = (len(sold_items) / total_items * 100) if total_items > 0 else 0

    # Averages
    avg_sale_price = total_revenue / len(sold_items) if sold_items else 0
    avg_purchase_cost = total_investment / len(all_items) if all_items else 0

    # Get total expenses (one-time + recurring for current year)
    current_year = datetime.now().year
    current_month = datetime.now().month

    # One-time expenses
    one_time_expenses = db.query(Expense).all()
    total_one_time = sum(e.amount for e in one_time_expenses)

    # Recurring expenses (calculate for all active periods)
    recurring_expenses = db.query(RecurringExpense).filter(RecurringExpense.is_active == True).all()
    total_recurring = 0
    for rec in recurring_expenses:
        start = rec.start_date
        end = rec.end_date or date.today()
        frequency = rec.frequency.value.lower() if rec.frequency else "monthly"

        if frequency == "yearly":
            # Count years this yearly expense has been active
            years_active = end.year - start.year + 1
            total_recurring += rec.amount * max(0, years_active)
        else:
            # Count months this monthly expense has been active
            months_active = (end.year - start.year) * 12 + (end.month - start.month) + 1
            total_recurring += rec.amount * max(0, months_active)

    total_expenses = total_one_time + total_recurring
    net_profit = total_profit - total_expenses

    # This month stats
    today = date.today()
    this_month_sold = [p for p in sold_items if p.sale_date and p.sale_date.year == today.year and p.sale_date.month == today.month]
    this_month_revenue = sum(p.sale_price or 0 for p in this_month_sold)
    this_month_profit = sum(p.profit for p in this_month_sold)
    this_month_items_sold = len(this_month_sold)

    return DashboardStats(
        total_revenue=total_revenue,
        total_profit=total_profit,
        total_items_sold=len(sold_items),
        total_items_unsold=len(unsold_items),
        total_investment=total_investment,
        avg_profit_per_item=total_profit / len(sold_items) if sold_items else 0,
        avg_days_to_sell=avg_days,
        roi=roi,
        profit_margin=profit_margin,
        unsold_stock_value=unsold_stock_value,
        total_expenses=total_expenses,
        net_profit=net_profit,
        sell_through_rate=sell_through_rate,
        avg_sale_price=avg_sale_price,
        avg_purchase_cost=avg_purchase_cost,
        this_month_revenue=this_month_revenue,
        this_month_profit=this_month_profit,
        this_month_items_sold=this_month_items_sold
    )


@router.get("/stats/monthly", response_model=List[MonthlyStats])
def get_monthly_stats(year: Optional[int] = None, db: Session = Depends(get_db)):
    """Get monthly financial breakdown"""
    from dateutil.relativedelta import relativedelta

    if not year:
        year = datetime.now().year

    # Get all sold items for the year (revenue comes when sold)
    sold_items = db.query(Product).filter(
        Product.status == ProductStatus.SOLD,
        extract('year', Product.sale_date) == year
    ).all()

    # Get all items that have installment payments affecting this year
    # This includes items purchased in previous year with installments extending into this year
    all_items_with_payments = db.query(Product).filter(
        Product.purchase_date != None,
        Product.purchase_cost != None
    ).all()

    # Get all one-time expenses for the year
    expenses = db.query(Expense).filter(
        extract('year', Expense.expense_date) == year
    ).all()

    # Get recurring expenses that apply to this year
    recurring_expenses = db.query(RecurringExpense).filter(
        RecurringExpense.start_date <= date(year, 12, 31),
        (RecurringExpense.end_date >= date(year, 1, 1)) | (RecurringExpense.end_date == None)
    ).all()

    # Group by month
    monthly_data = {}

    # Initialize all months
    for month in range(1, 13):
        monthly_data[month] = {
            "revenue": 0,
            "profit": 0,
            "items_sold": 0,
            "expenses": 0,
            "recurring_expenses": 0,
            "stock_purchases": 0,
            "items_purchased": 0
        }

    # Add revenue from sales (money IN - when items are sold)
    for item in sold_items:
        if item.sale_date:
            month_key = item.sale_date.month
            monthly_data[month_key]["revenue"] += item.sale_price or 0
            monthly_data[month_key]["profit"] += item.profit
            monthly_data[month_key]["items_sold"] += 1

    # Add stock purchases with installment support (money OUT)
    for item in all_items_with_payments:
        if not item.purchase_date or not item.purchase_cost:
            continue

        installments = item.payment_installments or 1
        installment_amount = item.purchase_cost / installments

        # Calculate which months get payments
        for i in range(installments):
            # Each installment is paid in consecutive months starting from purchase_date
            payment_date = item.purchase_date + relativedelta(months=i)

            # Only count if payment falls in the requested year
            if payment_date.year == year:
                monthly_data[payment_date.month]["stock_purchases"] += installment_amount
                if i == 0:  # Only count item once (in first payment month)
                    monthly_data[payment_date.month]["items_purchased"] += 1

    # Add one-time expenses (money OUT)
    for expense in expenses:
        month_key = expense.expense_date.month
        monthly_data[month_key]["expenses"] += expense.amount

    # Add recurring expenses (money OUT)
    for r in recurring_expenses:
        if not r.is_active:
            continue
        frequency = r.frequency.value.lower() if r.frequency else "monthly"

        if frequency == "yearly":
            # Yearly expenses only apply in the month matching the start_date's month
            expense_month = r.start_date.month
            month_start = date(year, expense_month, 1)
            if expense_month == 12:
                month_end = date(year, 12, 31)
            else:
                month_end = date(year, expense_month + 1, 1)
            # Check if this year falls within the expense's active period
            if r.start_date.year <= year and (r.end_date is None or r.end_date >= month_start):
                monthly_data[expense_month]["recurring_expenses"] += r.amount
        else:
            # Monthly expenses apply every month
            for month in range(1, 13):
                month_start = date(year, month, 1)
                if month == 12:
                    month_end = date(year, 12, 31)
                else:
                    month_end = date(year, month + 1, 1)
                # Check if this recurring expense applies to this month
                if r.start_date <= month_end and (r.end_date is None or r.end_date >= month_start):
                    monthly_data[month]["recurring_expenses"] += r.amount

    # Convert to list
    month_names = ["jan", "feb", "mar", "apr", "mai", "jun",
                   "jul", "aug", "sep", "oct", "nov", "dec"]

    result = []
    for month in range(1, 13):
        data = monthly_data[month]
        total_expenses = data["expenses"] + data["recurring_expenses"]
        # Cashflow = Money IN (revenue) - Money OUT (stock purchases + all expenses)
        cashflow = data["revenue"] - data["stock_purchases"] - total_expenses
        # Net profit = Gross profit - expenses (not including stock purchases, those are in gross profit)
        net_profit = data["profit"] - total_expenses

        result.append(MonthlyStats(
            month=month_names[month - 1],
            year=year,
            revenue=data["revenue"],
            profit=data["profit"],  # Gross profit
            net_profit=net_profit,  # After expenses
            cashflow=cashflow,
            items_sold=data["items_sold"],
            expenses=total_expenses + data["stock_purchases"]  # Total money out
        ))

    return result


@router.get("/stats/expense-categories")
def get_expense_categories(db: Session = Depends(get_db)):
    """Get unique expense categories"""
    categories = db.query(Expense.category).distinct().all()
    return [c[0] for c in categories]


# Preset expense categories
EXPENSE_CATEGORIES = [
    "Storage",
    "Shipping",
    "Platform Fees",
    "Packaging",
    "Marketing",
    "Software/Tools",
    "Other"
]


# Recurring expense schemas
class RecurringExpenseCreate(BaseModel):
    amount: float
    category: str
    description: Optional[str] = None
    frequency: str = "monthly"  # "monthly" or "yearly"
    start_date: str  # Accept string, parse later
    end_date: Optional[str] = None
    is_active: bool = True


class RecurringExpenseUpdate(BaseModel):
    amount: Optional[float] = None
    category: Optional[str] = None
    description: Optional[str] = None
    frequency: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_active: Optional[bool] = None


class RecurringExpenseResponse(BaseModel):
    id: int
    amount: float
    category: str
    description: Optional[str]
    frequency: str
    start_date: date
    end_date: Optional[date]
    is_active: bool

    class Config:
        from_attributes = True


# Recurring expense endpoints
@router.get("/recurring-expenses", response_model=List[RecurringExpenseResponse])
def get_recurring_expenses(db: Session = Depends(get_db)):
    """Get all recurring expenses"""
    expenses = db.query(RecurringExpense).order_by(RecurringExpense.start_date.desc()).all()
    return [
        RecurringExpenseResponse(
            id=e.id,
            amount=e.amount,
            category=e.category,
            description=e.description,
            frequency=e.frequency.value.lower() if e.frequency else "monthly",
            start_date=e.start_date,
            end_date=e.end_date,
            is_active=e.is_active
        )
        for e in expenses
    ]


@router.post("/recurring-expenses", response_model=RecurringExpenseResponse)
def create_recurring_expense(expense: RecurringExpenseCreate, db: Session = Depends(get_db)):
    """Create a recurring expense"""
    # Convert lowercase to uppercase for enum
    freq = ExpenseFrequency(expense.frequency.upper())
    db_expense = RecurringExpense(
        amount=expense.amount,
        category=expense.category,
        description=expense.description,
        frequency=freq,
        start_date=parse_date_string(expense.start_date),
        end_date=parse_date_string(expense.end_date) if expense.end_date else None,
        is_active=expense.is_active
    )
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return RecurringExpenseResponse(
        id=db_expense.id,
        amount=db_expense.amount,
        category=db_expense.category,
        description=db_expense.description,
        frequency=db_expense.frequency.value.lower(),
        start_date=db_expense.start_date,
        end_date=db_expense.end_date,
        is_active=db_expense.is_active
    )


@router.put("/recurring-expenses/{expense_id}", response_model=RecurringExpenseResponse)
def update_recurring_expense(expense_id: int, expense: RecurringExpenseUpdate, db: Session = Depends(get_db)):
    """Update a recurring expense"""
    db_expense = db.query(RecurringExpense).filter(RecurringExpense.id == expense_id).first()
    if not db_expense:
        raise HTTPException(status_code=404, detail="Recurring expense not found")

    update_data = expense.dict(exclude_unset=True)

    # Parse date fields
    for date_field in ['start_date', 'end_date']:
        if date_field in update_data and update_data[date_field]:
            update_data[date_field] = parse_date_string(update_data[date_field])

    # Convert frequency string to enum
    if 'frequency' in update_data and update_data['frequency']:
        update_data['frequency'] = ExpenseFrequency(update_data['frequency'].upper())

    for key, value in update_data.items():
        setattr(db_expense, key, value)

    db.commit()
    db.refresh(db_expense)
    return RecurringExpenseResponse(
        id=db_expense.id,
        amount=db_expense.amount,
        category=db_expense.category,
        description=db_expense.description,
        frequency=db_expense.frequency.value.lower() if db_expense.frequency else "monthly",
        start_date=db_expense.start_date,
        end_date=db_expense.end_date,
        is_active=db_expense.is_active
    )


@router.delete("/recurring-expenses/{expense_id}")
def delete_recurring_expense(expense_id: int, db: Session = Depends(get_db)):
    """Delete a recurring expense"""
    db_expense = db.query(RecurringExpense).filter(RecurringExpense.id == expense_id).first()
    if not db_expense:
        raise HTTPException(status_code=404, detail="Recurring expense not found")

    db.delete(db_expense)
    db.commit()
    return {"message": "Recurring expense deleted"}


@router.get("/categories")
def get_categories():
    """Get preset expense categories"""
    return EXPENSE_CATEGORIES


# Expense summary endpoints
class MonthlySummary(BaseModel):
    month: int
    year: int
    month_name: str
    one_time_total: float
    recurring_total: float
    total: float
    expense_count: int
    expenses: List[ExpenseResponse] = []


class CategorySummary(BaseModel):
    category: str
    total: float
    count: int
    avg_per_month: float


@router.get("/expenses/summary/monthly")
def get_expenses_monthly_summary(year: Optional[int] = None, db: Session = Depends(get_db)):
    """Get expenses grouped by month"""
    if not year:
        year = datetime.now().year

    month_names = ["January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"]

    # Get one-time expenses for the year
    one_time_expenses = db.query(Expense).filter(
        extract('year', Expense.expense_date) == year
    ).all()

    # Get recurring expenses that were active during the year
    recurring_expenses = db.query(RecurringExpense).filter(
        RecurringExpense.start_date <= date(year, 12, 31),
        (RecurringExpense.end_date >= date(year, 1, 1)) | (RecurringExpense.end_date == None)
    ).all()

    # Build monthly summary
    result = []
    for month in range(1, 13):
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year, 12, 31)
        else:
            month_end = date(year, month + 1, 1)

        # One-time expenses for this month
        month_expenses = [e for e in one_time_expenses if e.expense_date.month == month]
        one_time_total = sum(e.amount for e in month_expenses)

        # Recurring expenses active this month
        recurring_total = 0
        for r in recurring_expenses:
            if not r.is_active:
                continue
            frequency = r.frequency.value.lower() if r.frequency else "monthly"

            if frequency == "yearly":
                # Yearly expenses only apply in the month matching start_date's month
                if month == r.start_date.month:
                    # Check if this year falls within the expense's active period
                    if r.start_date.year <= year and (r.end_date is None or r.end_date >= month_start):
                        recurring_total += r.amount
            else:
                # Monthly expenses apply every month they're active
                if r.start_date <= month_end and (r.end_date is None or r.end_date >= month_start):
                    recurring_total += r.amount

        result.append({
            "month": month,
            "year": year,
            "month_name": month_names[month - 1],
            "one_time_total": one_time_total,
            "recurring_total": recurring_total,
            "total": one_time_total + recurring_total,
            "expense_count": len(month_expenses),
            "expenses": [ExpenseResponse(
                id=e.id,
                amount=e.amount,
                category=e.category,
                description=e.description,
                expense_date=e.expense_date
            ) for e in month_expenses]
        })

    return result


@router.get("/expenses/summary/category")
def get_expenses_category_summary(year: Optional[int] = None, db: Session = Depends(get_db)):
    """Get expenses grouped by category"""
    if not year:
        year = datetime.now().year

    # Get one-time expenses for the year
    one_time_expenses = db.query(Expense).filter(
        extract('year', Expense.expense_date) == year
    ).all()

    # Get recurring expenses
    recurring_expenses = db.query(RecurringExpense).filter(
        RecurringExpense.start_date <= date(year, 12, 31),
        (RecurringExpense.end_date >= date(year, 1, 1)) | (RecurringExpense.end_date == None),
        RecurringExpense.is_active == True
    ).all()

    # Calculate periods active for each recurring expense
    def periods_active_in_year(r, year):
        frequency = r.frequency.value.lower() if r.frequency else "monthly"

        if frequency == "yearly":
            # Yearly expenses occur once per year if active
            expense_month = r.start_date.month
            month_start = date(year, expense_month, 1)
            if r.start_date.year <= year and (r.end_date is None or r.end_date >= month_start):
                return 1
            return 0
        else:
            # Monthly expenses - count active months
            count = 0
            for month in range(1, 13):
                month_start = date(year, month, 1)
                if month == 12:
                    month_end = date(year, 12, 31)
                else:
                    month_end = date(year, month + 1, 1)
                if r.start_date <= month_end and (r.end_date is None or r.end_date >= month_start):
                    count += 1
            return count

    # Group by category
    category_data = {}

    for e in one_time_expenses:
        if e.category not in category_data:
            category_data[e.category] = {"total": 0, "count": 0}
        category_data[e.category]["total"] += e.amount
        category_data[e.category]["count"] += 1

    for r in recurring_expenses:
        periods = periods_active_in_year(r, year)
        if r.category not in category_data:
            category_data[r.category] = {"total": 0, "count": 0}
        category_data[r.category]["total"] += r.amount * periods
        category_data[r.category]["count"] += periods

    # Convert to list
    result = []
    for category, data in category_data.items():
        result.append({
            "category": category,
            "total": data["total"],
            "count": data["count"],
            "avg_per_month": data["total"] / 12
        })

    return sorted(result, key=lambda x: x["total"], reverse=True)
