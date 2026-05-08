import logging
from app import db
from app.models.product_model import Product

logger = logging.getLogger(__name__)

def get_all_products(category=None, min_price=None, max_price=None, sort=None, search=None):
    query = Product.query.filter_by(is_active=True)
    if category:
        query = query.filter(Product.category == category)
    if min_price is not None:
        query = query.filter(Product.discounted_price >= min_price)
    if max_price is not None:
        query = query.filter(Product.discounted_price <= max_price)
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
    if sort == "price_asc":
        query = query.order_by(Product.discounted_price.asc())
    elif sort == "price_desc":
        query = query.order_by(Product.discounted_price.desc())
    elif sort == "rating":
        query = query.order_by(Product.rating.desc())
    else:
        query = query.order_by(Product.popularity_score.desc())
    return query.all()

def get_product_by_id(product_id):
    return Product.query.get(product_id)

def create_product(data):
    try:
        p = Product(
            name=data["name"],
            brand=data.get("brand", ""),
            category=data.get("category", ""),
            subcategory=data.get("subcategory", ""),
            price=float(data.get("price", 0)),
            discounted_price=float(data.get("discounted_price") or data.get("price", 0)),
            discount_percent=float(data.get("discount_percent", 0)),
            rating=float(data.get("rating", 0)),
            reviews_count=int(data.get("reviews_count", 0)),
            popularity_score=float(data.get("popularity_score", 0)),
            stock_status=data.get("stock_status", "In Stock"),
            stock_quantity=int(data.get("stock_quantity", 100)),
            description=data.get("description", ""),
            image_url=data.get("image_url", ""),
        )
        db.session.add(p)
        db.session.commit()
        return p
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating product: {e}")
        raise

def update_product(product_id, data):
    p = Product.query.get_or_404(product_id)
    for field in ["name", "brand", "category", "subcategory", "price", "discounted_price",
                  "discount_percent", "stock_status", "stock_quantity", "description", "image_url"]:
        if field in data:
            setattr(p, field, data[field])
    db.session.commit()
    return p

def delete_product(product_id):
    p = Product.query.get_or_404(product_id)
    p.is_active = False
    db.session.commit()

def get_categories():
    rows = db.session.query(Product.category).distinct().filter(Product.category.isnot(None)).all()
    return sorted([r[0] for r in rows if r[0]])

def get_low_stock_products(threshold=20):
    return Product.query.filter(
        Product.stock_quantity <= threshold, Product.is_active == True
    ).order_by(Product.stock_quantity.asc()).all()
