import os
from flask import Flask, jsonify
from flask_cors import CORS
from app.config import config_by_name
from app.extensions import mongo, init_redis
from app.services.search_service import search_service

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
    search_service.init_app(app)
    
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
    app.register_blueprint(forms_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(public_dashboard_bp)
    
    return app
