"""
Migration script to add enhanced CRM features:
1. Create recurring_costs table
2. Create notifications table
3. Create product_metrics table
4. Add vat_amount, original_cost, notes columns to sales table
5. Backfill product_metrics for existing products with days_listed calculation
"""
import sqlite3
from datetime import datetime
import sys


def migrate_database():
    """Add new tables and columns to the database"""
    conn = sqlite3.connect('crm.db')
    cursor = conn.cursor()

    try:
        print("Starting database migration...")

        # Check which tables/columns exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]

        # 1. Create recurring_costs table
        if 'recurring_costs' not in existing_tables:
            print("Creating recurring_costs table...")
            cursor.execute("""
                CREATE TABLE recurring_costs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    amount FLOAT NOT NULL,
                    frequency VARCHAR(20) NOT NULL DEFAULT 'monthly',
                    category VARCHAR(100),
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    start_date TIMESTAMP NOT NULL,
                    end_date TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX idx_recurring_costs_is_active ON recurring_costs(is_active)")
            print("✓ Created recurring_costs table")
        else:
            print("✓ recurring_costs table already exists")

        # 2. Create notifications table
        if 'notifications' not in existing_tables:
            print("Creating notifications table...")
            cursor.execute("""
                CREATE TABLE notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type VARCHAR(50) NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    message TEXT NOT NULL,
                    read BOOLEAN NOT NULL DEFAULT 0,
                    metadata JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX idx_notifications_type ON notifications(type)")
            cursor.execute("CREATE INDEX idx_notifications_read ON notifications(read)")
            cursor.execute("CREATE INDEX idx_notifications_created_at ON notifications(created_at)")
            print("✓ Created notifications table")
        else:
            print("✓ notifications table already exists")

        # 3. Create product_metrics table
        if 'product_metrics' not in existing_tables:
            print("Creating product_metrics table...")
            cursor.execute("""
                CREATE TABLE product_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL UNIQUE,
                    days_listed INTEGER DEFAULT 0,
                    view_count INTEGER DEFAULT 0,
                    times_price_reduced INTEGER DEFAULT 0,
                    original_listing_price FLOAT,
                    optimal_price_suggestion FLOAT,
                    last_price_check TIMESTAMP,
                    updated_at TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE UNIQUE INDEX idx_product_metrics_product_id ON product_metrics(product_id)")
            print("✓ Created product_metrics table")

            # Backfill product_metrics for existing products
            print("Backfilling product_metrics for existing products...")
            cursor.execute("SELECT id, price, created_at FROM products")
            products = cursor.fetchall()

            for product_id, price, created_at in products:
                # Calculate days_listed
                if created_at:
                    created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    days_listed = (datetime.now() - created_date).days
                else:
                    days_listed = 0

                cursor.execute("""
                    INSERT INTO product_metrics (product_id, days_listed, original_listing_price, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (product_id, days_listed, price, datetime.now()))

            print(f"✓ Backfilled product_metrics for {len(products)} products")
        else:
            print("✓ product_metrics table already exists")

        # 4. Add new columns to sales table
        cursor.execute("PRAGMA table_info(sales)")
        sales_columns = [column[1] for column in cursor.fetchall()]

        if 'vat_amount' not in sales_columns:
            print("Adding vat_amount column to sales table...")
            cursor.execute("ALTER TABLE sales ADD COLUMN vat_amount FLOAT DEFAULT 0.0")
            print("✓ Added vat_amount column")
        else:
            print("✓ vat_amount column already exists")

        if 'original_cost' not in sales_columns:
            print("Adding original_cost column to sales table...")
            cursor.execute("ALTER TABLE sales ADD COLUMN original_cost FLOAT DEFAULT 0.0")
            print("✓ Added original_cost column")
        else:
            print("✓ original_cost column already exists")

        if 'notes' not in sales_columns:
            print("Adding notes column to sales table...")
            cursor.execute("ALTER TABLE sales ADD COLUMN notes TEXT")
            print("✓ Added notes column")
        else:
            print("✓ notes column already exists")

        # 5. Update net_profit for existing sales if needed
        print("Recalculating net_profit for existing sales...")
        cursor.execute("""
            UPDATE sales
            SET net_profit = sale_price - shipping_cost - platform_fee - payment_fee - vat_amount - original_cost
            WHERE net_profit IS NULL OR net_profit != (sale_price - shipping_cost - platform_fee - payment_fee - vat_amount - original_cost)
        """)
        updated_count = cursor.rowcount
        print(f"✓ Recalculated net_profit for {updated_count} sales")

        conn.commit()
        print("\n✅ Migration completed successfully!")
        print("\nNew tables created:")
        print("  - recurring_costs")
        print("  - notifications")
        print("  - product_metrics")
        print("\nNew columns added to sales:")
        print("  - vat_amount")
        print("  - original_cost")
        print("  - notes")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {str(e)}")
        sys.exit(1)

    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("CRM Database Migration - Enhanced Features")
    print("=" * 60)
    print()

    response = input("⚠️  This will modify your database. Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Migration cancelled.")
        sys.exit(0)

    print()
    migrate_database()
