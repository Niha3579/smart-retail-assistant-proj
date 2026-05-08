from app import db
from datetime import datetime

class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.String(50), unique=True, nullable=True)
    name = db.Column(db.String(200), nullable=False)
    brand = db.Column(db.String(100))
    category = db.Column(db.String(100))
    subcategory = db.Column(db.String(100))
    price = db.Column(db.Float, nullable=False, default=0.0)
    currency = db.Column(db.String(10), default="INR")
    discount_percent = db.Column(db.Float, default=0.0)
    discounted_price = db.Column(db.Float, default=0.0)
    rating = db.Column(db.Float, default=0.0)
    reviews_count = db.Column(db.Integer, default=0)
    popularity_score = db.Column(db.Float, default=0.0)
    stock_status = db.Column(db.String(50), default="In Stock")
    stock_quantity = db.Column(db.Integer, default=100)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True)

    cart_items = db.relationship("CartItem", backref="product", lazy=True)
    order_items = db.relationship("OrderItem", backref="product", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "name": self.name,
            "brand": self.brand,
            "category": self.category,
            "subcategory": self.subcategory,
            "price": self.price,
            "currency": self.currency,
            "discount_percent": self.discount_percent,
            "discounted_price": self.discounted_price,
            "rating": self.rating,
            "reviews_count": self.reviews_count,
            "popularity_score": self.popularity_score,
            "stock_status": self.stock_status,
            "stock_quantity": self.stock_quantity,
            "description": self.description,
            "image_url": self.image_url,
        }
