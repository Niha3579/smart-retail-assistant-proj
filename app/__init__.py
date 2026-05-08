import logging
import decimal
import json
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import config


class _Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        return super().default(obj)

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "user.login"

def create_app(env="development"):
    app = Flask(__name__)
    app.config.from_object(config[env])

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    app.json_encoder = _Encoder  # type: ignore

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from app.models import user_model, product_model, order_model, document_model  # noqa: F401

    from app.routes.admin_routes import admin_bp
    from app.routes.user_routes import user_bp
    from app.routes.api_routes import api_bp
    from app.routes.app import rag_bp

    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(user_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(rag_bp, url_prefix="/rag")

    # Register safe tojson filter that handles Decimal/numpy types
    import markupsafe

    @app.template_filter('safe_json')
    def safe_json_filter(value):
        def _convert(v):
            if isinstance(v, decimal.Decimal):
                return float(v)
            if isinstance(v, list):
                return [_convert(i) for i in v]
            if isinstance(v, dict):
                return {k: _convert(val) for k, val in v.items()}
            return v
        return markupsafe.Markup(json.dumps(_convert(value)))

    from app.models.user_model import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.errorhandler(404)
    def not_found(e):
        return {"error": "Not found"}, 404

    @app.errorhandler(500)
    def server_error(e):
        import traceback
        logging.error(traceback.format_exc())
        return {"error": "Internal server error"}, 500

    return app
