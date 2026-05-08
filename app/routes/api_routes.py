import logging
import os
import uuid
from flask import Blueprint, request, jsonify
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from sqlalchemy import func
from app.services import product_service, order_service, analytics_service
from app.services.chatbot_service import chatbot_service
from app.services.ai_service import ai_service
from app.ml.demand_forecast import predict_demand
from app import db
from app.models.order_model import Order, SalesRecord
from app.models.order_model import OrderItem
from app.models.product_model import Product

logger = logging.getLogger(__name__)
api_bp = Blueprint("api", __name__)
INGEST_TMP_DIR = os.path.join("uploads", "ingestion")
os.makedirs(INGEST_TMP_DIR, exist_ok=True)
INGEST_SESSIONS = {}


@api_bp.route("/products")
def api_products():
    products = product_service.get_all_products(
        category=request.args.get("category"),
        search=request.args.get("search"),
        sort=request.args.get("sort"),
    )
    return jsonify([p.to_dict() for p in products])


@api_bp.route("/products/<int:pid>")
def api_product(pid):
    p = product_service.get_product_by_id(pid)
    if not p:
        return jsonify({"error": "Not found"}), 404
    return jsonify(p.to_dict())


@api_bp.route("/predict-demand/<product_id>")
def api_predict(product_id):
    from app.models.product_model import Product
    p = Product.query.filter_by(product_id=product_id).first() or Product.query.get(product_id)
    category = p.category if p else None
    result = predict_demand(product_id, category=category)
    return jsonify(result)


@api_bp.route("/agent-chat", methods=["POST"])
def api_agent_chat():
    data = request.get_json() or {}
    query = data.get("message", "").strip()
    if not query:
        return jsonify({"error": "message required"}), 400

    # Primary chatbot path: FAQ + support + database insights.
    result = chatbot_service.answer(query, user=current_user)
    # Fallback to multi-agent router for broader analytical queries.
    if result.get("source") == "fallback":
        from app.services.agents.router import agent_router
        result = agent_router.route_query(query)
    if not isinstance(result, dict):
        result = {"agent": "System", "response": str(result), "confidence": 0.0}
    result.setdefault("agent", "System")
    result.setdefault("response", "I could not generate a response right now.")
    result.setdefault("confidence", 0.0)
    return jsonify(result)


@api_bp.route("/upload-document", methods=["POST"])
@login_required
def api_upload_document():
    """Upload a PDF document for RAG processing."""
    if "document" not in request.files:
        return jsonify({"error": "No document file provided"}), 400

    file = request.files["document"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    supported_exts = {".pdf", ".txt", ".csv"}
    ext = os.path.splitext(file.filename.lower())[1]
    if ext not in supported_exts:
        return jsonify({"error": "Only PDF, TXT, and CSV files are allowed"}), 400

    try:
        # Save file to uploads/documents/
        upload_dir = "uploads/documents"
        os.makedirs(upload_dir, exist_ok=True)

        original_name = secure_filename(file.filename)
        safe_name = f"{uuid.uuid4().hex[:8]}_{original_name}"
        file_path = os.path.join(upload_dir, safe_name)
        file.save(file_path)

        # Process with document agent
        from app.services.agents.document_agent import document_agent
        success = document_agent.upload_document(file_path, safe_name)

        if success:
            # Save to database for tracking
            from app.models.document_model import Document
            from app import db
            from datetime import datetime

            doc = Document(
                filename=safe_name,
                content=f"{ext.lstrip('.').upper()} uploaded at {datetime.utcnow()}"
            )
            db.session.add(doc)
            db.session.commit()

            return jsonify({
                "message": "Document uploaded and processed successfully",
                "filename": safe_name
            })
        else:
            # Clean up file if processing failed
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({"error": "Failed to process document"}), 500

    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        return jsonify({"error": "Internal server error"}), 500


@api_bp.route("/delete-document/<filename>", methods=["DELETE"])
@login_required
def api_delete_document(filename):
    """Delete a document from the system."""
    try:
        ext = os.path.splitext(filename.lower())[1]
        success = True
        if ext == ".pdf":
            # Remove from vector store for embedded PDFs
            from app.services.agents.document_agent import document_agent
            success = document_agent.delete_document(filename)

        if success:
            # Remove from database
            from app.models.document_model import Document
            from app import db

            doc = Document.query.filter_by(filename=filename).first()
            if doc:
                db.session.delete(doc)
                db.session.commit()

            # Remove physical file
            import os
            file_path = os.path.join("uploads/pdfs", filename)
            if os.path.exists(file_path):
                os.remove(file_path)

            return jsonify({"message": f"Document {filename} deleted successfully"})
        else:
            return jsonify({"error": "Document not found or failed to delete"}), 404

    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        return jsonify({"error": "Internal server error"}), 500


@api_bp.route("/orders")
def api_orders():
    orders = order_service.get_all_orders()
    return jsonify([o.to_dict() for o in orders])


@api_bp.route("/orders/update-status", methods=["POST"])
def api_update_order_status():
    data = request.get_json() or {}
    order_id = data.get("order_id")
    status = data.get("status")
    if not order_id or not status:
        return jsonify({"error": "order_id and status required"}), 400
    order = order_service.update_order_status(order_id, status)
    return jsonify(order.to_dict())


@api_bp.route("/anomalies")
def api_anomalies():
    return jsonify(analytics_service.get_anomalies())


@api_bp.route("/analytics-summary")
def api_analytics_summary():
    kpis = analytics_service.get_dashboard_kpis()
    days = request.args.get("days", default=90, type=int)
    if days not in (30, 60, 90):
        days = 90
    trend = analytics_service.get_sales_trend(days)
    by_cat = analytics_service.get_revenue_by_category()
    return jsonify({"kpis": kpis, "trend": {"labels": trend.get("labels",[]), "revenue": trend.get("revenue",[])}, "by_category": {"labels": by_cat.get("labels",[]), "amounts": by_cat.get("amounts",[])}})


@api_bp.route("/analytics/revenue")
def api_analytics_revenue():
    days = request.args.get("days", default=90, type=int)
    if days not in (30, 60, 90, 180, 365):
        days = 90
    trend = analytics_service.get_sales_trend(days)
    return jsonify({"labels": trend.get("labels", []), "values": trend.get("revenue", [])})


@api_bp.route("/analytics/top-products")
def api_analytics_top_products():
    rows = (
        db.session.query(
            func.coalesce(SalesRecord.product_name, SalesRecord.product_id).label("product"),
            func.sum(SalesRecord.revenue).label("revenue"),
        )
        .group_by(func.coalesce(SalesRecord.product_name, SalesRecord.product_id))
        .order_by(func.sum(SalesRecord.revenue).desc())
        .limit(10)
        .all()
    )
    if not rows:
        rows = (
            db.session.query(
                Product.name.label("product"),
                func.sum(OrderItem.quantity * OrderItem.unit_price).label("revenue"),
            )
            .join(OrderItem, Product.id == OrderItem.product_id)
            .group_by(Product.name)
            .order_by(func.sum(OrderItem.quantity * OrderItem.unit_price).desc())
            .limit(10)
            .all()
        )
    return jsonify({
        "labels": [str(r.product or "Unknown") for r in rows],
        "values": [round(float(r.revenue or 0), 2) for r in rows],
    })


@api_bp.route("/analytics/category")
def api_analytics_category():
    data = analytics_service.get_revenue_by_category()
    return jsonify({"labels": data.get("labels", []), "values": data.get("amounts", [])})


@api_bp.route("/analytics/region")
def api_analytics_region():
    rows = (
        db.session.query(
            func.coalesce(SalesRecord.region, "Unknown").label("region"),
            func.sum(SalesRecord.revenue).label("revenue"),
        )
        .group_by(func.coalesce(SalesRecord.region, "Unknown"))
        .order_by(func.sum(SalesRecord.revenue).desc())
        .all()
    )
    return jsonify({
        "labels": [str(r.region) for r in rows],
        "values": [round(float(r.revenue or 0), 2) for r in rows],
    })


@api_bp.route("/analytics/orders")
def api_analytics_orders():
    order_rows = (
        db.session.query(
            func.date(Order.created_at).label("day"),
            func.count(Order.id).label("orders"),
            func.sum(Order.total_amount).label("revenue"),
        )
        .group_by(func.date(Order.created_at))
        .order_by(func.date(Order.created_at))
        .all()
    )

    if order_rows:
        labels = [str(r.day) for r in order_rows]
        orders = [int(r.orders or 0) for r in order_rows]
        revenue = [float(r.revenue or 0) for r in order_rows]
        total_orders = sum(orders)
        total_revenue = sum(revenue)
    else:
        sales_rows = (
            db.session.query(
                SalesRecord.date.label("day"),
                func.count(func.distinct(SalesRecord.order_id)).label("orders"),
                func.sum(SalesRecord.revenue).label("revenue"),
            )
            .filter(SalesRecord.order_id.isnot(None))
            .group_by(SalesRecord.date)
            .order_by(SalesRecord.date)
            .all()
        )
        labels = [str(r.day) for r in sales_rows]
        orders = [int(r.orders or 0) for r in sales_rows]
        revenue = [float(r.revenue or 0) for r in sales_rows]
        total_orders = sum(orders)
        total_revenue = sum(revenue)

    aov = round((total_revenue / total_orders), 2) if total_orders else 0.0
    aov_series = [round((revenue[i] / orders[i]), 2) if orders[i] else 0 for i in range(len(labels))]
    return jsonify({
        "labels": labels,
        "orders": orders,
        "aov": aov_series,
        "kpis": {
            "total_revenue": round(total_revenue, 2),
            "total_orders": int(total_orders),
            "avg_order_value": aov,
        },
    })


@api_bp.route("/system-health")
def api_system_health():
    import os
    import psutil
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory().percent
    except Exception:
        cpu, mem = 0, 0
    return jsonify({"status": "healthy", "cpu": cpu, "memory": mem, "db": "connected"})


@api_bp.route("/upload-csv", methods=["POST"])
def api_upload_csv():
    import datetime
    if not request.files:
        return jsonify({"status": "error", "error": "No files uploaded."}), 400

    uploaded = {}
    for field in ("products_file", "sales_file"):
        f = request.files.get(field)
        if not f or not f.filename:
            continue
        if not f.filename.lower().endswith(".csv"):
            return jsonify({"status": "error", "error": f"{field} must be a CSV file."}), 400
        file_id = f"{uuid.uuid4().hex}.csv"
        path = os.path.join(INGEST_TMP_DIR, file_id)
        f.save(path)
        uploaded[field] = {"file_id": file_id, "original_name": secure_filename(f.filename)}

    if not uploaded:
        return jsonify({"status": "error", "error": "No CSV files selected."}), 400

    session_id = uuid.uuid4().hex
    INGEST_SESSIONS[session_id] = {
        "uploaded": uploaded,
        "created_at": datetime.datetime.utcnow().isoformat(),
        "validated": False,
        "loaded": False,
    }
    return jsonify({"status": "ok", "session_id": session_id, "uploaded": uploaded})


@api_bp.route("/validate-csv", methods=["POST"])
def api_validate_csv():
    from app.services.data_loader import (
        PRODUCTS_REQUIRED_COLUMNS,
        SALES_REQUIRED_COLUMNS,
        validate_csv_quality,
    )
    data = request.get_json() or {}
    session_id = data.get("session_id")
    session = INGEST_SESSIONS.get(session_id)
    if not session:
        return jsonify({"status": "error", "error": "Invalid or expired session_id."}), 400

    validation = {}
    uploaded = session.get("uploaded", {})
    if "products_file" in uploaded:
        p = os.path.join(INGEST_TMP_DIR, uploaded["products_file"]["file_id"])
        validation["products"] = validate_csv_quality(p, PRODUCTS_REQUIRED_COLUMNS)
    if "sales_file" in uploaded:
        p = os.path.join(INGEST_TMP_DIR, uploaded["sales_file"]["file_id"])
        validation["sales"] = validate_csv_quality(p, SALES_REQUIRED_COLUMNS)

    is_valid = True
    if validation.get("products") and not validation["products"]["valid"]:
        is_valid = False
    if validation.get("sales") and not validation["sales"]["valid"]:
        is_valid = False

    session["validation"] = validation
    session["validated"] = is_valid
    return jsonify({"status": "ok" if is_valid else "error", "session_id": session_id, "validation": validation})


@api_bp.route("/load-data", methods=["POST"])
def api_load_data():
    from app.services.data_loader import ingest_products_csv, ingest_sales_csv
    data = request.get_json() or {}
    session_id = data.get("session_id")
    session = INGEST_SESSIONS.get(session_id)
    if not session:
        return jsonify({"status": "error", "error": "Invalid or expired session_id."}), 400
    if not session.get("validated"):
        return jsonify({"status": "error", "error": "Validation failed or not run yet."}), 400

    uploaded = session.get("uploaded", {})
    results = {"products_loaded": 0, "sales_loaded": 0, "products_error": None, "sales_error": None}

    if "products_file" in uploaded:
        p = os.path.join(INGEST_TMP_DIR, uploaded["products_file"]["file_id"])
        out = ingest_products_csv(p)
        results["products_loaded"] = out["loaded"]
        results["products_error"] = out["error"]
    if "sales_file" in uploaded:
        p = os.path.join(INGEST_TMP_DIR, uploaded["sales_file"]["file_id"])
        out = ingest_sales_csv(p)
        results["sales_loaded"] = out["loaded"]
        results["sales_error"] = out["error"]

    ok = not results["products_error"] and not results["sales_error"]
    session["loaded"] = ok
    session["load_result"] = results
    return jsonify({"status": "ok" if ok else "error", "session_id": session_id, **results}), (200 if ok else 400)


@api_bp.route("/train-ml", methods=["POST"])
def api_train_ml():
    data = request.get_json() or {}
    session_id = data.get("session_id")
    session = INGEST_SESSIONS.get(session_id) if session_id else None
    if session_id and not session:
        return jsonify({"status": "error", "error": "Invalid or expired session_id."}), 400
    if session_id and not session.get("loaded"):
        return jsonify({"status": "error", "error": "Load to DB must complete before ML training."}), 400

    from app.ml.train_forecast import run as run_forecast_train
    from app.ml.train_anomaly import run as run_anomaly_train

    forecast_result = run_forecast_train()
    anomaly_result = run_anomaly_train()
    return jsonify({
        "status": "ok",
        "forecast": forecast_result,
        "anomaly": anomaly_result,
        "analytics_enabled": True,
    })


@api_bp.route("/data-ingest", methods=["POST"])
def api_data_ingest():
    from app.services.data_loader import ingest_products_csv, ingest_sales_csv
    import tempfile

    if not request.files:
        return jsonify({"status": "error", "error": "No files uploaded."}), 400

    results = {
        "status": "ok",
        "products_loaded": 0,
        "sales_loaded": 0,
        "products_error": None,
        "sales_error": None,
        "validation": {},
    }

    def _is_csv(filename):
        return bool(filename) and filename.lower().endswith(".csv")

    if "products_file" in request.files:
        f = request.files["products_file"]
        if f and f.filename:
            if not _is_csv(f.filename):
                results["products_error"] = "Products file must be a .csv"
            else:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                    f.save(tmp.name)
                    tmp_path = tmp.name
                try:
                    out = ingest_products_csv(tmp_path)
                    results["products_loaded"] = out["loaded"]
                    results["products_error"] = out["error"]
                    results["validation"]["products"] = out["validation"]
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)

    if "sales_file" in request.files:
        f = request.files["sales_file"]
        if f and f.filename:
            if not _is_csv(f.filename):
                results["sales_error"] = "Sales file must be a .csv"
            else:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                    f.save(tmp.name)
                    tmp_path = tmp.name
                try:
                    out = ingest_sales_csv(tmp_path)
                    results["sales_loaded"] = out["loaded"]
                    results["sales_error"] = out["error"]
                    results["validation"]["sales"] = out["validation"]
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)

    if results["products_error"] or results["sales_error"]:
        results["status"] = "partial_success" if (results["products_loaded"] or results["sales_loaded"]) else "error"
        return jsonify(results), 400 if results["status"] == "error" else 200

    return jsonify(results)


@api_bp.route("/cart", methods=["GET"])
@login_required
def api_cart():
    cart = order_service.get_cart(current_user.id)
    if not cart:
        return jsonify({"items": [], "total": 0})
    items = [
        {
            "id": i.id,
            "product_id": i.product_id,
            "product_name": i.product.name,
            "quantity": i.quantity,
            "unit_price": i.product.discounted_price or i.product.price,
            "image_url": i.product.image_url,
        }
        for i in cart.items
    ]
    total = sum(i["unit_price"] * i["quantity"] for i in items)
    return jsonify({"items": items, "total": total})


@api_bp.route("/cart", methods=["POST"])
@login_required
def api_add_to_cart():
    data = request.get_json() or {}
    order_service.add_to_cart(current_user.id, data["product_id"], data.get("quantity", 1))
    return jsonify({"status": "added"})


@api_bp.route("/cart/<int:item_id>", methods=["DELETE"])
@login_required
def api_remove_from_cart(item_id):
    order_service.remove_from_cart(current_user.id, item_id)
    return jsonify({"status": "removed"})
