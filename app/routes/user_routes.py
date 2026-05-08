import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user_model import User
from app.services import product_service, order_service
from app import db

logger = logging.getLogger(__name__)
user_bp = Blueprint("user", __name__, template_folder="../templates/user")


@user_bp.route("/")
def home():
    featured = product_service.get_all_products(sort="rating")[:8]
    categories = product_service.get_categories()
    return render_template("user/home.html", featured=featured, categories=categories)


@user_bp.route("/products")
def products():
    category = request.args.get("category")
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    sort = request.args.get("sort", "popular")
    search = request.args.get("search")
    products_list = product_service.get_all_products(
        category=category, min_price=min_price, max_price=max_price, sort=sort, search=search
    )
    categories = product_service.get_categories()
    return render_template(
        "user/products.html",
        products=products_list,
        categories=categories,
        selected_category=category,
        sort=sort,
        search=search or "",
    )


@user_bp.route("/product/<int:pid>")
def product_detail(pid):
    product = product_service.get_product_by_id(pid)
    if not product or not product.is_active:
        flash("Product not found.", "danger")
        return redirect(url_for("user.products"))
    related = product_service.get_all_products(category=product.category)[:4]
    related = [p for p in related if p.id != product.id][:3]
    return render_template("user/product_detail.html", product=product, related=related)


@user_bp.route("/cart")
@login_required
def cart():
    cart_obj = order_service.get_cart(current_user.id)
    items = cart_obj.items if cart_obj else []
    total = sum((i.product.discounted_price or i.product.price) * i.quantity for i in items)
    return render_template("user/cart.html", items=items, total=total)


@user_bp.route("/cart/add", methods=["POST"])
@login_required
def add_to_cart():
    product_id = request.form.get("product_id", type=int)
    quantity = request.form.get("quantity", 1, type=int)
    if product_id:
        order_service.add_to_cart(current_user.id, product_id, quantity)
        flash("Added to cart!", "success")
    return redirect(request.referrer or url_for("user.cart"))


@user_bp.route("/cart/remove/<int:item_id>", methods=["POST"])
@login_required
def remove_from_cart(item_id):
    order_service.remove_from_cart(current_user.id, item_id)
    flash("Item removed.", "info")
    return redirect(url_for("user.cart"))


@user_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    cart_obj = order_service.get_cart(current_user.id)
    items = cart_obj.items if cart_obj else []
    total = sum((i.product.discounted_price or i.product.price) * i.quantity for i in items)

    if request.method == "POST":
        address = request.form.get("address", "").strip()
        if not address:
            flash("Please provide a shipping address.", "warning")
            return render_template("user/checkout.html", items=items, total=total)
        try:
            order = order_service.create_order_from_cart(current_user, address)
            flash(f"Order #{order.id} placed successfully! Payment is mocked.", "success")
            return redirect(url_for("user.home"))
        except Exception as e:
            flash(str(e), "danger")

    return render_template("user/checkout.html", items=items, total=total)


@user_bp.route("/orders")
@login_required
def orders():
    orders_list = order_service.get_user_orders(current_user.id)
    return render_template("user/orders.html", orders=orders_list)


@user_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("user.home"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("user.home"))
        flash("Invalid email or password.", "danger")
    return render_template("user/login.html")


@user_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("user.home"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "warning")
        else:
            user = User(name=name, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Welcome! Your account has been created.", "success")
            return redirect(url_for("user.home"))
    return render_template("user/register.html")


@user_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("user.home"))
