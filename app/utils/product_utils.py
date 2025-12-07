import hashlib
import time
from typing import Optional


def generate_sku(title: str, category: Optional[str] = None) -> str:
    """
    Generate a unique SKU for a product.
    Format: {CATEGORY_PREFIX}-{TITLE_HASH}-{TIMESTAMP}

    Example: ELEC-A7B2C-1234567890
    """
    # Get category prefix (first 4 letters, uppercase)
    if category:
        prefix = category[:4].upper()
    else:
        prefix = "PROD"

    # Create a hash from the title (first 5 chars)
    title_hash = hashlib.md5(title.encode()).hexdigest()[:5].upper()

    # Get timestamp (last 6 digits)
    timestamp = str(int(time.time()))[-6:]

    # Combine to create SKU
    sku = f"{prefix}-{title_hash}-{timestamp}"

    return sku


def calculate_investment(expression: str) -> Optional[float]:
    """
    Safely evaluate a mathematical expression for investment calculation.
    Supports basic operations: +, -, *, /, (, )

    Example: "1550/30" -> 51.67
    """
    if not expression:
        return None

    try:
        # Remove whitespace
        expression = expression.strip()

        # Only allow safe mathematical characters
        allowed_chars = set('0123456789+-*/.()')
        if not all(c in allowed_chars or c.isspace() for c in expression):
            raise ValueError("Invalid characters in expression")

        # Evaluate the expression safely
        result = eval(expression, {"__builtins__": {}}, {})

        # Ensure result is a number
        if isinstance(result, (int, float)):
            return round(float(result), 2)
        else:
            raise ValueError("Expression did not evaluate to a number")

    except Exception as e:
        raise ValueError(f"Invalid investment calculation: {str(e)}")
