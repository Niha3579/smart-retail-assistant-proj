from app import db
from datetime import datetime

class Cart(db.Model):
    __tablename__ = "carts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    items = db.relationship("CartItem", backref="cart", lazy=True, cascade="all, delete-orphan")

class CartItem(db.Model):
    __tablename__ = "cart_items"

    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey("carts.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Integer, default=1)

class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    customer_name = db.Column(db.String(150))
    customer_email = db.Column(db.String(200))
    shipping_address = db.Column(db.Text)
    total_amount = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(50), default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship("OrderItem", backref="order", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "customer_name": self.customer_name,
            "customer_email": self.customer_email,
            "shipping_address": self.shipping_address,
            "total_amount": self.total_amount,
            "status": self.status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M"),
            "items": [item.to_dict() for item in self.items],
        }

class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, default=0.0)

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "product_name": self.product.name if self.product else "",
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "subtotal": self.quantity * self.unit_price,
        }

class SalesRecord(db.Model):
    __tablename__ = "sales_records"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(50), index=True)
    date = db.Column(db.Date)
    product_id = db.Column(db.String(50))
    product_name = db.Column(db.String(200))
    category = db.Column(db.String(100))
    units_sold = db.Column(db.Integer, default=0)
    revenue = db.Column(db.Float, default=0.0)
    region = db.Column(db.String(100))
    channel = db.Column(db.String(100))
    customer_name = db.Column(db.String(150))
    customer_email = db.Column(db.String(200))
    status = db.Column(db.String(50), default="Completed")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
