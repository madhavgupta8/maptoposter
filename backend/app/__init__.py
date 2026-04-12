from flask import Flask
from flask_cors import CORS

from app.config import Config
from app.routes.geocode import bp as geocode_bp
from app.routes.health import bp as health_bp
from app.routes.jobs import bp as jobs_bp
from app.routes.themes import bp as themes_bp


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": Config.CORS_ORIGINS}})

    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(themes_bp, url_prefix="/api")
    app.register_blueprint(geocode_bp, url_prefix="/api")
    app.register_blueprint(jobs_bp, url_prefix="/api")
    return app
