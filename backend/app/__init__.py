import os
from flask import Flask, jsonify
from flask_cors import CORS
from app.config import config_by_name
from app.extensions import mongo, init_redis, init_limiter
from app.services.search_service import search_service
from app.utils.security_middleware import security_middleware

def create_app(config_name=None):
    if not config_name:
        config_name = os.environ.get("FLASK_ENV", "development")
        
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])
    
    # Initialize CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Initialize Extensions
    mongo.init_app(app)
    init_redis(app)
    init_limiter(app)
    search_service.init_app(app)
    
    # Initialize Security Middleware
    security_middleware.init_app(app)
    
    # Register error handlers
    from app.utils.error_handler import register_error_handlers
    register_error_handlers(app)
    
    # Initialize OpenAPI documentation
    from app.utils.openapi_generator import openapi_generator
    openapi_generator.init_app(app)
    
    # Register Health Check Endpoint
    @app.route("/api/health", methods=["GET"])
    def health_check():
        return jsonify({
            "status": "healthy",
            "version": "1.0.0",
            "services": {
                "mongodb": "connected" if mongo.db is not None else "disconnected"
            }
        }), 200
        
    # Register blueprints
    from app.routes.forms import forms_bp
    from app.routes.dashboard import dashboard_bp, public_dashboard_bp
    from app.routes.sync import sync_bp
    from app.routes.notifications import notifications_bp
    from app.routes.auth import auth_bp
    from app.routes.auth import admin_bp
    from app.routes.identity import identity_bp
    from app.routes.compliance import compliance_bp
    from app.routes.analysis import analysis_bp
    from app.routes.plugins import plugins_bp
    from app.routes.uploads import uploads_bp
    from app.routes.api_v1 import api_v1_bp
    app.register_blueprint(forms_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(public_dashboard_bp)
    app.register_blueprint(sync_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(identity_bp)
    app.register_blueprint(compliance_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(plugins_bp)
    app.register_blueprint(uploads_bp)
    app.register_blueprint(api_v1_bp)

    return app
