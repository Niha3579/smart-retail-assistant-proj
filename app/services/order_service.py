import logging
from app import db
from app.models.order_model import Order, OrderItem, Cart, CartItem, SalesRecord
from app.models.product_model import Product
from sqlalchemy import func, or_
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

def get_all_orders():
    return Order.query.order_by(Order.created_at.desc()).all()

def get_current_orders(page=1, limit=15, search=""):
    query = Order.query
    if search:
        search_term = f"%{search}%"
        try:
            order_id_match = int(search)
        except (TypeError, ValueError):
            order_id_match = None

        filters = [
            Order.customer_name.ilike(search_term),
            Order.customer_email.ilike(search_term),
        ]
        if order_id_match is not None:
            filters.append(Order.id == order_id_match)
        query = query.filter(or_(*filters))

    pagination = query.order_by(Order.created_at.desc()).paginate(page=page, per_page=limit, error_out=False)
    orders = []
    for order in pagination.items:
        orders.append(
            {
                "id": order.id,
                "customer_name": order.customer_name,
                "customer_email": order.customer_email,
                "shipping_address": order.shipping_address,
                "total_amount": order.total_amount,
                "status": order.status,
                "created_at": order.created_at,
                "items": [item.to_dict() for item in order.items],
            }
        )
    return orders, pagination


def get_user_orders(user_id):
    """Return all previous orders for a user (latest first)."""
    return Order.query.filter_by(user_id=user_id).order_by(Order.created_at.desc()).all()


def get_sales_dataset_orders(search=""):
    query = db.session.query(
        SalesRecord.order_id.label("order_id"),
        func.max(SalesRecord.customer_name).label("customer_name"),
        func.max(SalesRecord.customer_email).label("customer_email"),
        func.sum(SalesRecord.revenue).label("total_amount"),
        func.max(SalesRecord.status).label("status"),
        func.max(SalesRecord.created_at).label("created_at"),
    ).filter(SalesRecord.order_id.isnot(None))

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                SalesRecord.order_id.ilike(search_term),
                SalesRecord.customer_email.ilike(search_term),
                SalesRecord.product_name.ilike(search_term),
            )
        )

    query = query.group_by(SalesRecord.order_id)
    grouped_orders = query.order_by(func.max(SalesRecord.created_at).desc()).all()

    orders_list = []
    for go in grouped_orders:
        order_id = str(go.order_id)
        orders_list.append({
            "id": order_id,
            "customer_name": go.customer_name,
            "customer_email": go.customer_email,
            "total_amount": float(go.total_amount or 0),
            "status": go.status,
            "created_at": go.created_at,
            "source": "sales_dataset",
        })

    return orders_list


def get_grouped_orders(page=1, limit=15, search=""):
    return get_sales_dataset_orders(search=search)

def get_order_by_id(order_id):
    return Order.query.get_or_404(order_id)

def update_order_status(order_id, status):
    order = Order.query.get_or_404(order_id)
    order.status = status
    db.session.commit()
    return order

def get_orders_summary():
    current_total = Order.query.count()
    sales_total = db.session.query(func.count(func.distinct(SalesRecord.order_id))).filter(SalesRecord.order_id.isnot(None)).scalar() or 0
    pending = Order.query.filter_by(status="Pending").count()
    completed = Order.query.filter_by(status="Completed").count()
    cancelled = Order.query.filter_by(status="Cancelled").count()
    return {
        "total": current_total + sales_total,
        "current_total": current_total,
        "sales_total": sales_total,
        "pending": pending,
        "completed": completed,
        "cancelled": cancelled,
    }

def create_order_from_cart(user, shipping_address):
    try:
        cart = Cart.query.filter_by(user_id=user.id).first()
        if not cart or not cart.items:
            raise ValueError("Cart is empty")

        order_id_str = f"ORD-{str(uuid.uuid4())[:8].upper()}"

        # We keep the original Order for user history if needed,
        # but also insert into SalesRecord for Admin display as requested.
        total = sum(
            (item.product.discounted_price or item.product.price) * item.quantity
            for item in cart.items
        )

        order = Order(
            user_id=user.id,
            customer_name=user.name,
            customer_email=user.email,
            shipping_address=shipping_address,
            total_amount=total,
            status="Pending",
        )
        db.session.add(order)
        db.session.flush()

        for ci in cart.items:
            unit_price = ci.product.discounted_price or ci.product.price
            # Insert into OrderItem for user consistency
            oi = OrderItem(order_id=order.id, product_id=ci.product_id, quantity=ci.quantity, unit_price=unit_price)
            db.session.add(oi)

            # Insert into SalesRecord as requested
            sr = SalesRecord(
                order_id=str(order.id),
                date=datetime.utcnow().date(),
                product_id=str(ci.product_id),
                product_name=ci.product.name,
                category=ci.product.category,
                units_sold=ci.quantity,
                revenue=unit_price * ci.quantity,
                customer_name=user.name,
                customer_email=user.email,
                status="Pending",
            )
            db.session.add(sr)

        db.session.delete(cart)
        db.session.commit()
        return order
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating order: {e}")
        raise

def get_cart(user_id):
    return Cart.query.filter_by(user_id=user_id).first()

def add_to_cart(user_id, product_id, quantity=1):
    cart = Cart.query.filter_by(user_id=user_id).first()
    if not cart:
        cart = Cart(user_id=user_id)
        db.session.add(cart)
        db.session.flush()

    existing = CartItem.query.filter_by(cart_id=cart.id, product_id=product_id).first()
    if existing:
        existing.quantity += quantity
    else:
        item = CartItem(cart_id=cart.id, product_id=product_id, quantity=quantity)
        db.session.add(item)
    db.session.commit()

def remove_from_cart(user_id, item_id):
    cart = Cart.query.filter_by(user_id=user_id).first()
    if cart:
        item = CartItem.query.filter_by(id=item_id, cart_id=cart.id).first()
        if item:
            db.session.delete(item)
            db.session.commit()
