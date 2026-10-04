import os

from flask import Flask

from .config import Config
from .extensions import csrf, db, limiter, login_manager, talisman
from .models import User


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Init extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    csrf.init_app(app)
    limiter.init_app(app)

    # Disable HTTPS forcing for local development
    is_prod = os.environ.get("FLASK_ENV") == "production"
    talisman.init_app(
        app,
        force_https=is_prod,
        content_security_policy={
            "default-src": ["'self'"],
            "style-src": ["'self'", "'unsafe-inline'"],
            "script-src": ["'self'", "'unsafe-inline'", "https://cdn.tailwindcss.com"],
            "img-src": ["'self'", "data:"],  # <--- Added "data:" to allow Base64 pictures
        },
    )

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from .blueprints.api import api_bp
    from .blueprints.auth import auth_bp
    from .blueprints.web import web_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(web_bp)

    with app.app_context():
        db.create_all()

    return app
