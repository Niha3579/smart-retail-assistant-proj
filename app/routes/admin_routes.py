import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.services import product_service, order_service, analytics_service
from app.models.product_model import Product
from app.models.order_model import SalesRecord
from app.models.document_model import Document
from app import db
from sqlalchemy import func
import os
from datetime import datetime
import uuid
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)
admin_bp = Blueprint("admin", __name__, template_folder="../templates/admin")


@admin_bp.route("/")
@admin_bp.route("/dashboard")
def dashboard():
    kpis = analytics_service.get_dashboard_kpis()
    try:
        trend_data = analytics_service.get_sales_trend(30)
        trend_labels = list(trend_data.get("labels", []))
        trend_revenue = list(trend_data.get("revenue", []))
    except Exception:
        trend_labels, trend_revenue = [], []
    anomalies = analytics_service.get_anomalies()[:3]
    top_products = (
        Product.query.filter_by(is_active=True)
        .order_by(Product.popularity_score.desc())
        .limit(5)
        .all()
    )
    return render_template(
        "admin/dashboard.html",
        kpis=kpis,
        trend_labels=trend_labels,
        trend_revenue=trend_revenue,
        anomalies=anomalies,
        top_products=top_products,
        active_page="dashboard",
    )


@admin_bp.route("/products")
def products():
    page = request.args.get("page", 1, type=int)
    category = request.args.get("category")
    search = request.args.get("search")
    stock = request.args.get("stock")
    query = Product.query.filter_by(is_active=True)
    if category:
        query = query.filter(Product.category == category)
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
    if stock:
        query = query.filter(Product.stock_status == stock)
    pagination = query.order_by(Product.popularity_score.desc()).paginate(page=page, per_page=15, error_out=False)
    products_list = pagination.items
    categories = product_service.get_categories()
    return render_template(
        "admin/products.html",
        products=products_list,
        pagination=pagination,
        categories=categories,
        active_page="products",
        selected_category=category,
        selected_stock=stock,
        search=search or "",
    )


@admin_bp.route("/products/add", methods=["POST"])
def add_product():
    try:
        product_service.create_product(request.form.to_dict())
        flash("Product added successfully.", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    return redirect(url_for("admin.products"))


@admin_bp.route("/products/edit/<int:pid>", methods=["POST"])
def edit_product(pid):
    try:
        product_service.update_product(pid, request.form.to_dict())
        flash("Product updated.", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    return redirect(url_for("admin.products"))


@admin_bp.route("/products/delete/<int:pid>", methods=["POST"])
def delete_product(pid):
    product_service.delete_product(pid)
    flash("Product removed.", "warning")
    return redirect(url_for("admin.products"))


@admin_bp.route("/orders")
def orders():
    search = request.args.get("search", "")

    summary = order_service.get_orders_summary()
    sales_orders = order_service.get_sales_dataset_orders(search=search)

    return render_template(
        "admin/orders.html",
        summary=summary,
        sales_orders=sales_orders,
        search=search,
        active_page="orders",
    )


@admin_bp.route("/sales")
def sales():
    records = SalesRecord.query.order_by(SalesRecord.date.desc()).limit(200).all()
    return render_template(
        "admin/sales.html",
        records=records,
        active_page="sales",
    )


@admin_bp.route("/predictions")
def predictions():
    products_list = Product.query.filter_by(is_active=True).order_by(Product.name).all()
    return render_template(
        "admin/predictions.html",
        products=products_list,
        active_page="predictions",
    )


@admin_bp.route("/analytics")
def analytics():  # noqa: C901
    power_bi_url = os.environ.get("POWER_BI_URL")

    try:
        trend_data = analytics_service.get_sales_trend(90)
        trend_labels = list(trend_data.get("labels", []))
        trend_revenue = list(trend_data.get("revenue", []))
    except Exception:
        trend_labels, trend_revenue = [], []
    try:
        by_cat = analytics_service.get_revenue_by_category()
        cat_labels = list(by_cat.get("labels", []))
        cat_amounts = list(by_cat.get("amounts", []))
    except Exception:
        cat_labels, cat_amounts = [], []
    return render_template(
        "admin/analytics.html",
        trend_labels=trend_labels,
        trend_revenue=trend_revenue,
        cat_labels=cat_labels,
        cat_amounts=cat_amounts,
        power_bi_url=power_bi_url,
        active_page="analytics",
    )


@admin_bp.route("/assistant")
def assistant():
    documents = Document.query.order_by(Document.created_at.desc()).all()
    return render_template("admin/assistant.html", documents=documents, active_page="assistant")

@admin_bp.route("/assistant/upload", methods=["POST"])
def assistant_upload():
    if "document" not in request.files:
        flash("No file provided.", "danger")
        return redirect(url_for("admin.assistant"))

    file = request.files["document"]
    if file.filename == "":
        flash("No selected file.", "danger")
        return redirect(url_for("admin.assistant"))

    allowed_exts = {".pdf", ".txt", ".csv"}
    _, ext = os.path.splitext(file.filename.lower())
    if ext not in allowed_exts:
        flash("Only PDF, TXT, and CSV files are allowed.", "warning")
        return redirect(url_for("admin.assistant"))

    # Size limit (e.g., 5MB)
    file.seek(0, os.SEEK_END)
    size = file.tell()
    if size > 5 * 1024 * 1024:
        flash("File size must be under 5MB.", "warning")
        return redirect(url_for("admin.assistant"))
    file.seek(0)

    try:
        # Save file to uploads/documents/ with a unique prefix so repeated uploads do not collide.
        upload_dir = os.path.join("uploads", "documents")
        os.makedirs(upload_dir, exist_ok=True)

        stored_name = secure_filename(file.filename)
        unique_name = f"{uuid.uuid4().hex[:8]}_{stored_name}"
        file_path = os.path.join(upload_dir, unique_name)
        file.save(file_path)

        from app.services.agents.document_agent import document_agent

        success = document_agent.upload_document(file_path, unique_name)
        if not success:
            if os.path.exists(file_path):
                os.remove(file_path)
            flash("Failed to process document.", "danger")
            return redirect(url_for("admin.assistant"))

        content_note = f"{ext.lstrip('.').upper()} uploaded and indexed at {datetime.utcnow()}"
        if ext in {".txt", ".csv"}:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as handle:
                    raw_content = handle.read().strip()
                if raw_content:
                    content_note = raw_content[:10000]
            except Exception:
                pass

        # Save to database for tracking
        doc = Document(filename=unique_name, content=content_note)
        db.session.add(doc)
        db.session.commit()

        flash("Document uploaded and processed successfully.", "success")

    except Exception as e:
        flash(f"Error uploading document: {e}", "danger")

    return redirect(url_for("admin.assistant"))

@admin_bp.route("/assistant/document/<int:doc_id>/delete", methods=["POST"])
def assistant_delete_doc(doc_id):
    doc = Document.query.get_or_404(doc_id)

    ext = os.path.splitext(doc.filename.lower())[1]
    success = True
    if ext == ".pdf":
        # Delete from vector store only for PDFs.
        from app.services.agents.document_agent import document_agent
        success = document_agent.delete_document(doc.filename)

    if success:
        # Remove from database
        db.session.delete(doc)
        db.session.commit()

        # Remove physical file
        for folder in (os.path.join("uploads", "documents"), os.path.join("uploads", "pdfs")):
            file_path = os.path.join(folder, doc.filename)
            if os.path.exists(file_path):
                os.remove(file_path)

        flash(f"Document {doc.filename} deleted successfully.", "success")
    else:
        flash(f"Failed to delete document {doc.filename}.", "danger")

    return redirect(url_for("admin.assistant"))

@admin_bp.route("/anomalies")
def anomalies():
    anomaly_list = analytics_service.get_anomalies()
    return render_template("admin/anomalies.html", anomalies=anomaly_list, active_page="anomalies")


@admin_bp.route("/settings")
def settings():
    import os
    env_vars = {
        "FLASK_ENV": os.environ.get("FLASK_ENV", "development"),
        "DATABASE_URL": "***" + os.environ.get("DATABASE_URL", "")[-10:],
        "OPENAI_API_KEY": "***" if os.environ.get("OPENAI_API_KEY") else "Not set",
        "AZURE_SQL_URL": "***" if os.environ.get("AZURE_SQL_URL") else "Not set",
    }
    return render_template("admin/settings.html", env_vars=env_vars, active_page="settings")
