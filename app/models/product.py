from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Enum, Date, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum
import uuid
import time


def generate_sku():
    """Generate a unique SKU like RL-XXXXXXXX"""
    # Use timestamp + random to ensure uniqueness
    timestamp = hex(int(time.time() * 1000))[-6:]  # Last 6 hex chars of timestamp
    random_part = uuid.uuid4().hex[:4].upper()  # 4 random hex chars
    return f"RL-{timestamp.upper()}{random_part}"


class ProductStatus(str, enum.Enum):
    ACTIVE = "active"
    POSTED = "posted"
    SOLD = "sold"
    PENDING = "pending"
    INACTIVE = "inactive"


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(20), unique=True, index=True, nullable=True)  # Unique SKU for cross-platform linking
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    images = Column(JSON, default=list)  # List of image URLs
    category = Column(String(100), nullable=True)
    size = Column(String(50), nullable=True)
    condition = Column(String(50), nullable=True)
    brand = Column(String(100), nullable=True)
    color = Column(String(50), nullable=True)
    status = Column(Enum(ProductStatus), default=ProductStatus.ACTIVE)

    # Inventory tracking fields
    purchase_date = Column(Date, nullable=True)  # Cand le-am cumparat
    received_date = Column(Date, nullable=True)  # Cand le-am primit
    purchase_cost = Column(Float, nullable=True)  # Investitie
    batch_name = Column(String(100), nullable=True)  # produs/batch name
    sale_price = Column(Float, nullable=True)  # pret vanzare
    sale_date = Column(Date, nullable=True)  # Data vanzare
    vat_amount = Column(Float, nullable=True)  # VAT
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=True)
    payment_installments = Column(Integer, default=1)  # Number of installments (1 = paid in full, 4 = 4x monthly)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    platform_listings = relationship("PlatformListing", back_populates="product", cascade="all, delete-orphan")
    sales = relationship("Sale", back_populates="product", cascade="all, delete-orphan")
    batch = relationship("Batch", back_populates="products")

    @property
    def profit(self):
        """Calculate profit (sale_price - purchase_cost)"""
        if self.sale_price is not None and self.purchase_cost is not None:
            return self.sale_price - self.purchase_cost
        elif self.purchase_cost is not None:
            return -self.purchase_cost  # Unsold = negative (investment)
        return 0

    @property
    def days_to_sell(self):
        """Calculate days from received date to sale date"""
        if self.sale_date and self.received_date:
            return (self.sale_date - self.received_date).days
        return None  # Return None when not sold, 0 when sold same day

    def __repr__(self):
        return f"<Product(id={self.id}, title='{self.title}', status='{self.status}')>"


class Batch(Base):
    """Track batches/lots of products purchased together"""
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # e.g., "dickies", "vintage wholesale lot"
    total_cost = Column(Float, nullable=False)  # Total investment for the batch
    item_count = Column(Integer, nullable=False)  # Number of items in batch
    purchase_date = Column(Date, nullable=True)
    received_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    products = relationship("Product", back_populates="batch")
    expenses = relationship("Expense", back_populates="batch")

    @property
    def cost_per_item(self):
        """Calculate cost per item"""
        if self.item_count > 0:
            return self.total_cost / self.item_count
        return 0

    @property
    def batch_expenses(self):
        """Total expenses linked to this batch (shipping, customs, etc.)"""
        return sum(e.amount for e in self.expenses) if self.expenses else 0

    @property
    def total_investment(self):
        """Total investment = batch cost + linked expenses"""
        return self.total_cost + self.batch_expenses

    @property
    def total_revenue(self):
        """Calculate total revenue from sold items"""
        return sum(p.sale_price or 0 for p in self.products if p.status == ProductStatus.SOLD)

    @property
    def total_profit(self):
        """Calculate total profit from sold items minus batch expenses"""
        raw_profit = sum(p.profit for p in self.products if p.status == ProductStatus.SOLD)
        return raw_profit - self.batch_expenses

    @property
    def items_sold(self):
        """Count sold items"""
        return sum(1 for p in self.products if p.status == ProductStatus.SOLD)

    @property
    def roi(self):
        """Calculate ROI percentage (profit / total investment including expenses)"""
        if self.total_investment > 0:
            return (self.total_profit / self.total_investment) * 100
        return 0

    def __repr__(self):
        return f"<Batch(id={self.id}, name='{self.name}', items={self.item_count})>"


class Expense(Base):
    """Track business expenses (shipping, consumables, marketing, etc.)"""
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    category = Column(String(100), nullable=False)  # consumables, shipping, marketing, etc.
    description = Column(String(255), nullable=True)
    expense_date = Column(Date, nullable=False)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=True)  # Optional link to batch

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    batch = relationship("Batch", back_populates="expenses")

    def __repr__(self):
        return f"<Expense(id={self.id}, category='{self.category}', amount={self.amount})>"


class ExpenseFrequency(str, enum.Enum):
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class RecurringExpense(Base):
    """Track recurring expenses (storage, subscriptions, etc.)"""
    __tablename__ = "recurring_expenses"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    category = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    frequency = Column(Enum(ExpenseFrequency), default=ExpenseFrequency.MONTHLY)  # monthly or yearly
    start_date = Column(Date, nullable=False)  # When this expense starts
    end_date = Column(Date, nullable=True)  # When it ends (null = indefinite)
    is_active = Column(Boolean, default=True)  # Can be paused manually

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<RecurringExpense(id={self.id}, category='{self.category}', amount={self.amount})>"
