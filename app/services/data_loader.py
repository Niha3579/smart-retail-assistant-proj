"""
Data ingestion service.
Loads products from CSV into the Product table.
Loads sales records from CSV into SalesRecord table.
"""
import os
import logging
import pandas as pd
from datetime import datetime
from app import db
from app.models.product_model import Product
from app.models.order_model import SalesRecord

logger = logging.getLogger(__name__)

PRODUCTS_CSV = os.path.join(os.path.dirname(__file__), "../../data/ecommerce_products_updated.csv")
SALES_CSV = os.path.join(os.path.dirname(__file__), "../../data/simulated_sales_data_2022_2025.csv")

PRODUCTS_REQUIRED_COLUMNS = ["product_id", "product_name", "category", "price", "discounted_price"]
SALES_REQUIRED_COLUMNS = ["order_id", "date", "product_id", "product_name", "category", "units_sold", "revenue"]


def _safe_int(value, default=0):
    try:
        if pd.isna(value):
            return default
        return int(float(value))
    except Exception:
        return default


def _safe_float(value, default=0.0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def validate_csv_columns(csv_path, required_columns):
    """
    Validate CSV columns and return normalized validation details.
    """
    df = pd.read_csv(csv_path, nrows=1)
    cols = [str(c).strip().lower() for c in df.columns]
    missing = [c for c in required_columns if c not in cols]
    return {
        "columns_present": cols,
        "missing_columns": missing,
        "valid": len(missing) == 0,
    }


def validate_csv_quality(csv_path, required_columns):
    """
    Basic validation + quality checks for ETL step.
    """
    df = pd.read_csv(csv_path)
    columns_info = validate_csv_columns(csv_path, required_columns)
    missing_required_values = {}

    for col in required_columns:
        if col in df.columns:
            missing_required_values[col] = int(df[col].isna().sum())

    duplicate_rows = int(df.duplicated().sum())

    return {
        **columns_info,
        "row_count": int(len(df)),
        "duplicate_rows": duplicate_rows,
        "missing_required_values": missing_required_values,
        "valid": columns_info["valid"] and len(df) > 0,
    }


def load_products_from_csv(csv_path=None):
    path = csv_path or PRODUCTS_CSV
    if not os.path.exists(path):
        logger.warning(f"Products CSV not found at {path}")
        return 0

    df = pd.read_csv(path)
    loaded = 0
    for _, row in df.iterrows():
        pid = str(row.get("product_id", "")).strip()
        if pid and Product.query.filter_by(product_id=pid).first():
            continue
        try:
            date_added = None
            raw_date = row.get("date_added")
            if raw_date and str(raw_date) != "nan":
                try:
                    date_added = datetime.strptime(str(raw_date), "%Y-%m-%d")
                except Exception:
                    date_added = datetime.utcnow()

            p = Product(
                product_id=pid or None,
                name=str(row.get("product_name", row.get("name", "Unknown"))).strip(),
                brand=str(row.get("brand", "")).strip(),
                category=str(row.get("category", "")).strip(),
                subcategory=str(row.get("subcategory", "")).strip(),
                price=float(row.get("price", 0) or 0),
                currency=str(row.get("currency", "INR")),
                discount_percent=float(row.get("discount_percent", 0) or 0),
                discounted_price=float(row.get("discounted_price", row.get("price", 0)) or 0),
                rating=float(row.get("rating", 0) or 0),
                reviews_count=int(row.get("reviews_count", 0) or 0),
                popularity_score=float(row.get("popularity_score", 0) or 0),
                stock_status=str(row.get("stock_status", "In Stock")),
                stock_quantity=100 if str(row.get("stock_status", "")) == "In Stock" else (
                    15 if str(row.get("stock_status", "")) == "Limited Stock" else 0
                ),
                description=str(row.get("description", "")),
                image_url=str(row.get("image_url", "")),
                date_added=date_added or datetime.utcnow(),
            )
            db.session.add(p)
            loaded += 1
        except Exception as e:
            logger.error(f"Error loading product row: {e}")
            continue

    db.session.commit()
    logger.info(f"Loaded {loaded} products from CSV")
    return loaded


def load_sales_from_csv(csv_path=None):
    path = csv_path or SALES_CSV
    if not os.path.exists(path):
        logger.warning(f"Sales CSV not found at {path}")
        return 0

    df = pd.read_csv(path)
    loaded = 0

    date_col = None
    for c in ["date", "Date", "order_date", "sale_date"]:
        if c in df.columns:
            date_col = c
            break

    prod_col = None
    for c in ["product_id", "Product_ID", "product"]:
        if c in df.columns:
            prod_col = c
            break

    name_col = None
    for c in ["product_name", "Product_Name", "name"]:
        if c in df.columns:
            name_col = c
            break

    cat_col = None
    for c in ["category", "Category"]:
        if c in df.columns:
            cat_col = c
            break

    rev_col = None
    for c in ["revenue", "Revenue", "total_revenue", "sales_amount", "amount"]:
        if c in df.columns:
            rev_col = c
            break

    units_col = None
    for c in ["units_sold", "Units_Sold", "quantity", "Quantity"]:
        if c in df.columns:
            units_col = c
            break

    region_col = None
    for c in ["region", "Region"]:
        if c in df.columns:
            region_col = c
            break

    channel_col = None
    for c in ["channel", "Channel", "sales_channel"]:
        if c in df.columns:
            channel_col = c
            break

    for _, row in df.iterrows():
        try:
            order_id = str(row["order_id"]).strip() if "order_id" in df.columns and pd.notna(row.get("order_id")) else None

            sale_date = None
            if date_col:
                try:
                    sale_date = pd.to_datetime(row[date_col]).date()
                except Exception:
                    pass

            sr = SalesRecord(
                date=sale_date,
                order_id=order_id,
                product_id=str(row[prod_col]).strip() if prod_col and pd.notna(row.get(prod_col)) else None,
                product_name=str(row[name_col]).strip() if name_col and pd.notna(row.get(name_col)) else None,
                category=str(row[cat_col]).strip() if cat_col and pd.notna(row.get(cat_col)) else None,
                units_sold=_safe_int(row[units_col]) if units_col else 0,
                revenue=_safe_float(row[rev_col]) if rev_col else 0.0,
                region=str(row[region_col]).strip() if region_col and pd.notna(row.get(region_col)) else None,
                channel=str(row[channel_col]).strip() if channel_col and pd.notna(row.get(channel_col)) else None,
            )
            db.session.add(sr)
            loaded += 1

            if loaded % 500 == 0:
                db.session.flush()
        except Exception as e:
            logger.error(f"Sales row error: {e}")
            continue

    db.session.commit()
    logger.info(f"Loaded {loaded} sales records")
    return loaded


def ingest_products_csv(csv_path):
    """
    Validate and ingest products CSV with structured response.
    """
    if not os.path.exists(csv_path):
        return {"loaded": 0, "error": "Products CSV file not found.", "validation": None}
    try:
        validation = validate_csv_columns(csv_path, PRODUCTS_REQUIRED_COLUMNS)
        if not validation["valid"]:
            return {
                "loaded": 0,
                "error": f"Missing required products columns: {', '.join(validation['missing_columns'])}",
                "validation": validation,
            }
        loaded = load_products_from_csv(csv_path)
        return {"loaded": loaded, "error": None, "validation": validation}
    except Exception as e:
        logger.error(f"Products ingestion failed: {e}")
        return {"loaded": 0, "error": str(e), "validation": None}


def ingest_sales_csv(csv_path):
    """
    Validate and ingest sales CSV with structured response.
    """
    if not os.path.exists(csv_path):
        return {"loaded": 0, "error": "Sales CSV file not found.", "validation": None}
    try:
        validation = validate_csv_columns(csv_path, SALES_REQUIRED_COLUMNS)
        if not validation["valid"]:
            return {
                "loaded": 0,
                "error": f"Missing required sales columns: {', '.join(validation['missing_columns'])}",
                "validation": validation,
            }
        loaded = load_sales_from_csv(csv_path)
        return {"loaded": loaded, "error": None, "validation": validation}
    except Exception as e:
        logger.error(f"Sales ingestion failed: {e}")
        return {"loaded": 0, "error": str(e), "validation": None}
