"""
Migration script to add new columns to products table:
- sku
- quantity
- investment_per_product
"""
import sqlite3
from app.utils.product_utils import generate_sku

def migrate_database():
    """Add new columns to products table"""
    conn = sqlite3.connect('crm.db')
    cursor = conn.cursor()

    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(products)")
        columns = [column[1] for column in cursor.fetchall()]

        # Add sku column if it doesn't exist
        if 'sku' not in columns:
            print("Adding 'sku' column...")
            cursor.execute("ALTER TABLE products ADD COLUMN sku VARCHAR(100)")

            # Generate SKUs for existing products
            cursor.execute("SELECT id, title, category FROM products")
            products = cursor.fetchall()

            for product_id, title, category in products:
                sku = generate_sku(title, category)
                # Ensure uniqueness
                while True:
                    cursor.execute("SELECT id FROM products WHERE sku = ?", (sku,))
                    if not cursor.fetchone():
                        break
                    sku = generate_sku(title + str(product_id), category)

                cursor.execute("UPDATE products SET sku = ? WHERE id = ?", (sku, product_id))

            # Create unique index on sku
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_products_sku ON products(sku)")
            print(f"Generated SKUs for {len(products)} existing products")

        # Add quantity column if it doesn't exist
        if 'quantity' not in columns:
            print("Adding 'quantity' column...")
            cursor.execute("ALTER TABLE products ADD COLUMN quantity INTEGER NOT NULL DEFAULT 1")

        # Add investment_per_product column if it doesn't exist
        if 'investment_per_product' not in columns:
            print("Adding 'investment_per_product' column...")
            cursor.execute("ALTER TABLE products ADD COLUMN investment_per_product FLOAT")

        conn.commit()
        print("Migration completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {str(e)}")
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    migrate_database()
